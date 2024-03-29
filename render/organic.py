import math

import cairo
import numpy as np
import torch
from PIL import Image
import torchvision.transforms.functional as TF

from render.renderinterface import RenderingInterface
from utils import map_number, Vector, perpendicular, normalize


class OrganicRenderer(RenderingInterface):
    def __init__(self, args):
        super(OrganicRenderer, self).__init__(args)

        self.img_size = args.img_size
        self.num_lines = args.num_lines

        self.device = args.device

        self.header_length = 1

        self.genotype_size = 13

        self.individual = None

    def chunks(self, array):
        return np.reshape(array, (self.num_lines, self.genotype_size))

    def generate_individual(self):
        return np.random.rand(self.num_lines, self.genotype_size).flatten()

    def to_adam(self, individual, gradients=True):
        self.individual = np.copy(individual)
        self.individual = self.chunks(self.individual)
        self.individual = torch.tensor(self.individual).float().to(self.device)

        if gradients:
            self.individual.requires_grad = True

        optimizer = torch.optim.Adam([self.individual], lr=1.0)

        return [optimizer]

    def get_individual(self):
        return self.individual.cpu().detach().numpy().flatten()

    def __str__(self):
        return "organic"

    def render(self):
        input_ind = self.individual
        input_ind = input_ind.cpu().detach().numpy()

        # split input array into header and rest
        head = input_ind[:self.header_length]
        rest = input_ind[self.header_length:]

        # determine background color from header
        R = head[0][0]
        G = head[0][1]
        B = head[0][2]

        # create the image and drawing context
        # im = Image.new('RGB', (size, size), (R, G, B))
        # draw = ImageDraw.Draw(im, 'RGB')

        ims = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.img_size, self.img_size)
        cr = cairo.Context(ims)

        cr.set_source_rgba(R, G, B, 1.0)  # everythingon cairo appears to be between 0 and 1
        cr.rectangle(0, 0, self.img_size, self.img_size)  # define a recatangle and then fill it
        cr.fill()

        # now draw lines

        min_size = 0.005 * self.img_size
        max_size = 0.15 * self.img_size

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        # main cicle begins

        for e in rest:
            R = e[0]
            G = e[1]
            B = e[2]
            w1 = map_number(e[3], 0, 1, min_size, max_size)
            w2 = map_number(e[4], 0, 1, min_size, max_size)

            input_ind = Vector(map_number(e[5], 0, 1, 0, self.img_size), map_number(e[6], 0, 1, 0, self.img_size))
            # a=Vector(500, 200)
            d = Vector(map_number(e[7], 0, 1, 0, self.img_size), map_number(e[8], 0, 1, 0, self.img_size))
            # d=Vector(200, 800)
            A = Vector(input_ind.x, input_ind.y)
            D = Vector(d.x, d.y)

            AD = D - A
            maxdist = AD.length() / 2

            b = input_ind + Vector(map_number(e[9], 0, 1, 0, maxdist) * np.sign(d.x - input_ind.x),
                                   map_number(e[10], 0, 1, 0, maxdist) * np.sign(d.y - input_ind.y))

            # b=a+Vector(-100, +150) #os sinais têm que ser compativeis com as direções
            # c=d+Vector(-100, -100) #os sinais têm que ser compativeis com as direções
            c = d + Vector(map_number(e[11], 0, 1, 0, maxdist) * np.sign(input_ind.x - d.x),
                           map_number(e[12], 0, 1, 0, maxdist) * np.sign(input_ind.y - d.y))

            cr.set_source_rgb(R, G, B)
            cr.set_line_width(1)

            cr.move_to(input_ind.x, input_ind.y)
            cr.curve_to(b.x, b.y, c.x, c.y, d.x, d.y)
            cr.stroke()

            B = Vector(b.x, b.y)
            AB = B - A
            AB_perp_normed = perpendicular(normalize(AB))
            a1 = A + AB_perp_normed * w1
            a2 = A - AB_perp_normed * w1
            b1 = B + AB_perp_normed * w1
            b2 = B - AB_perp_normed * w1

            C = Vector(c.x, c.y)
            CD = D - C
            CD_perp_normed = perpendicular(normalize(CD))
            c1 = C + CD_perp_normed * w2
            c2 = C - CD_perp_normed * w2
            d1 = D + CD_perp_normed * w2
            d2 = D - CD_perp_normed * w2

            cr.move_to(a2.x, a2.y)
            cr.line_to(a1.x, a1.y)
            cr.curve_to(b1.x, b1.y, c1.x, c1.y, d1.x, d1.y)
            cr.line_to(d2.x, d2.y)

            cr.move_to(d2.x, d2.y)
            cr.curve_to(c2.x, c2.y, b2.x, b2.y, a2.x, a2.y)
            cr.fill_preserve()
            cr.stroke()

            cr.arc(input_ind.x, input_ind.y, w1, AB_perp_normed.angle(), math.pi + AB_perp_normed.angle())
            cr.fill_preserve()
            cr.stroke()

            cr.arc(d.x, d.y, w2, math.pi + CD_perp_normed.angle(), CD_perp_normed.angle())
            cr.fill_preserve()
            cr.stroke()

        pilMode = 'RGB'
        # argbArray = numpy.fromstring( ims.get_data(), 'c' ).reshape( -1, 4 )
        argbArray = np.fromstring(bytes(ims.get_data()), 'c').reshape(-1, 4)
        rgbArray = argbArray[:, 2::-1]
        pilData = rgbArray.reshape(-1).tostring()
        pilImage = Image.frombuffer(pilMode,
                                    (ims.get_width(), ims.get_height()), pilData, "raw",
                                    pilMode, 0, 1)
        pilImage = pilImage.convert('RGB')

        return TF.to_tensor(pilImage).unsqueeze(0)
