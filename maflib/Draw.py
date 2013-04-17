#! /usr/bin/env python
# encoding: utf-8

from collections import defaultdict
import json

from waflib import TaskGen
from maflib import Experiment

import maflib.Utils as mUtils
from matplotlib import pyplot

def get_axis_name(axis):
    if type(axis) == str:
        return axis
    else:
        return axis['name']

class DrawResult(Experiment.ExperimentalTask):
    def __init__(self, env, generator):
        super(DrawResult, self).__init__(env=env, generator=generator)
        self.x_axis = env['x_axis']
        self.y_axis = env['y_axis']
        self.legend = env['legend']
        self.param_combs = env['param_combs']

    def run(self):
        fig = pyplot.figure()
        axes = fig.add_subplot(111)

        x_axis = self.env['x_axis']
        x_name = get_axis_name(x_axis)
        if type(x_axis) == dict and 'scale' in x_axis:
            axes.set_xscale(x_axis['scale'])

        y_axis = self.env['y_axis']
        y_name = get_axis_name(y_axis)
        y_conv = None
        if type(y_axis) == dict:
            if 'scale' in y_axis:
                axes.set_yscale(y_axis['scale'])
            if 'converter' in y_axis:
                y_conv = y_axis['converter']

        # 結果を読んで、パラメータリストに結果をくっつけて配列を作る。
        results = defaultdict(list)
        for result in self.inputs:
            param = mUtils.decode_parameterized_nodename(result.abspath().split('/').pop())
            param[y_name] = json.loads(result.read())[y_name]
            results[param[self.legend]].append(param)

        # TODO: マーカーを自動的に選ぶ仕組み整備
        markers = ['s', 'v', '^', '*', '+', 'D', 'h', 'H', 'o']
        i = 0

        keys = sorted(results.keys())
        for legend_value in keys:
            params = results[legend_value]

            xs = sorted(list(set(float(result[x_name]) for result in params)))
            x_to_y = {}
            for param in params:
                x_to_y[float(param[x_name])] = param[y_name]
            ys = [x_to_y[x] for x in xs]
            if y_conv:
                ys = map(y_conv, ys)
                print ys

            legend = '%s=%s' % (self.legend, legend_value)
            axes.plot(xs, ys, label=legend, marker=markers[i])

            i = (i + 1) % len(markers)

        axes.legend(loc='lower right')
        fig.savefig(self.outputs[0].abspath())

        return 0

@TaskGen.feature('draw')
def feature_draw(self):
    self.env['x_axis'] = self.x_axis
    self.env['y_axis'] = self.y_axis
    self.env['legend'] = self.legend

    param_combs = mUtils.load_params(self, self.result)
    self.env['param_combs'] = param_combs

    x_axis_name = get_axis_name(self.x_axis)
    divided_param_combs = mUtils.divide_param_combs(param_combs, [get_axis_name(self.x_axis), self.legend])

    for divided_param in divided_param_combs:
        results = []
        for var_param in divided_param[1]:
            param = divided_param[0].copy()
            for k, v in var_param.iteritems():
                param[k] = v
            results.append(mUtils.generate_parameterized_nodename(self.result, param))
        figure = mUtils.generate_parameterized_nodename(self.figure, divided_param[0])
        if figure[len(figure) - 1] == '/':
            figure += 'figure'
        figure += '.png'

        self.create_task('DrawResult',
                         src=[self.path.find_resource(result) for result in results],
                         tgt=self.path.find_or_declare(figure)
                         )