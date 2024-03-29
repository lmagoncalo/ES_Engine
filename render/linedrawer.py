import random

import numpy as np
import pydiffvg
import torch

from render.renderinterface import RenderingInterface


class LineDrawRenderer(RenderingInterface):
    def __init__(self, args):
        super(LineDrawRenderer, self).__init__(args)

        self.device = args.device

        self.num_lines = args.num_lines
        self.img_size = args.img_size

        self.max_width = 2 * self.img_size / 100
        self.min_width = 0.5 * self.img_size / 100

        self.stroke_length = 8

    def chunks(self, array):
        # array = torch.tensor(array, dtype=torch.float)
        # return array.view(self.num_lines, (self.num_segments * 3) + 1, 2)
        return np.reshape(array, (self.num_lines, (self.stroke_length * 3) + 1, 2))

    def bound(self, value, low, high):
        return max(low, min(high, value))

    def generate_individual(self):
        # Initialize Random Curves
        individual = []

        # Initialize Random Curves
        for i in range(self.num_lines):
            num_segments = self.stroke_length
            # num_control_points = torch.zeros(num_segments, dtype=torch.int32) + 2
            points = []
            p0 = (random.random(), random.random())
            points.append(p0)
            for j in range(num_segments):
                p1 = (random.random(), random.random())
                p2 = (random.random(), random.random())
                p3 = (random.random(), random.random())
                points.append(p1)
                points.append(p2)
                points.append(p3)
            points = torch.tensor(points)
            individual.append(np.array(points))

        individual = np.array(individual)
        print(individual.shape)

        return individual.flatten()

    def get_individual(self):
        individual = []
        for path in self.shapes[1:]:
            points = path.points.clone().detach()
            points[:, 0] /= self.img_size
            points[:, 1] /= self.img_size
            new_points = []
            for p, point in enumerate(points):
                if p == 0:
                    radius = 0.5
                    p_x = ((points[p][0] - 0.5) / radius) + 0.5
                    p_y = ((points[p][1] - 0.5) / radius) + 0.5
                    new_points.append([p_x, p_y])
                else:
                    radius = 1.0 / (self.stroke_length + 2)
                    p_x = ((points[p][0] - points[p - 1][0]) / radius) + 0.5
                    p_y = ((points[p][1] - points[p - 1][1]) / radius) + 0.5
                    new_points.append([p_x, p_y])

            new_points = np.array(new_points)
            individual.append(new_points)

        individual = np.array(individual).flatten()
        return individual

    def to_adam(self, individual, gradients=True):
        self.individual = np.copy(individual)

        self.individual = self.chunks(self.individual)
        self.individual = torch.tensor(self.individual).float().to(self.device)

        shapes = []
        shape_groups = []

        # background shape
        p0 = [0, 0]
        p1 = [self.img_size, self.img_size]
        path = pydiffvg.Rect(p_min=torch.tensor(p0), p_max=torch.tensor(p1))
        shapes.append(path)
        # https://encycolorpedia.com/f2eecb
        cell_color = torch.tensor([242 / 255.0, 238 / 255.0, 203 / 255.0, 1.0])
        path_group = pydiffvg.ShapeGroup(shape_ids=torch.tensor([len(shapes) - 1]), stroke_color=None,
                                         fill_color=cell_color)
        shape_groups.append(path_group)

        # Initialize Random Curves
        for i in range(self.num_lines):
            num_segments = self.stroke_length
            num_control_points = torch.zeros(num_segments, dtype=torch.int32) + 2
            points = []
            radius = 0.5
            p0 = (0.5 + radius * (self.individual[i][0][0] - 0.5), 0.5 + radius * (self.individual[i][0][1] - 0.5))
            points.append(p0)
            for j in range(num_segments):
                radius = 1.0 / (num_segments + 2)
                p1 = (p0[0] + radius * (self.individual[i][(j * 3) + 1][0] - 0.5), p0[1] + radius * (self.individual[i][(j * 3) + 1][1] - 0.5))
                p2 = (p1[0] + radius * (self.individual[i][(j * 3) + 2][0] - 0.5), p1[1] + radius * (self.individual[i][(j * 3) + 2][1] - 0.5))
                p3 = (p2[0] + radius * (self.individual[i][(j * 3) + 3][0] - 0.5), p2[1] + radius * (self.individual[i][(j * 3) + 3][1] - 0.5))
                points.append(p1)
                points.append(p2)
                points.append(p3)
                p0 = p3
            points = torch.tensor(points)
            points[:, 0] *= self.img_size
            points[:, 1] *= self.img_size
            path = pydiffvg.Path(num_control_points=num_control_points, points=points,
                                 stroke_width=torch.tensor(self.max_width / 10), is_closed=False)
            shapes.append(path)
            s_col = [0, 0, 0, 1]
            path_group = pydiffvg.ShapeGroup(shape_ids=torch.tensor([len(shapes) - 1]), fill_color=None,
                                             stroke_color=torch.tensor(s_col))
            shape_groups.append(path_group)

        points_vars = []
        stroke_width_vars = []
        for path in shapes[1:]:
            if gradients:
                path.points.requires_grad = True
            points_vars.append(path.points)

            if gradients:
                path.stroke_width.requires_grad = True
            stroke_width_vars.append(path.stroke_width)

        points_optim = torch.optim.Adam(points_vars, lr=1.0)
        width_optim = torch.optim.Adam(stroke_width_vars, lr=0.1)

        self.shapes = shapes
        self.shape_groups = shape_groups

        # return [points_optim, width_optim]
        return [points_optim]

    def __str__(self):
        return "linedraw"

    def render(self):
        render = pydiffvg.RenderFunction.apply
        scene_args = pydiffvg.RenderFunction.serialize_scene(self.img_size, self.img_size, self.shapes, self.shape_groups)
        img = render(self.img_size, self.img_size, 2, 2, 0, None, *scene_args)
        img = img[:, :, 3:4] * img[:, :, :3] + torch.ones(img.shape[0], img.shape[1], 3,
                                                          device=pydiffvg.get_device()) * (1 - img[:, :, 3:4])
        img = img[:, :, :3]
        img = img.unsqueeze(0)
        img = img.permute(0, 3, 1, 2)  # NHWC -> NCHW

        return img
