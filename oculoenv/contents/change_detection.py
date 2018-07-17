# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import random

from .base_content import BaseContent, ContentSprite


PLUS_MARKER_WIDTH = 0.15  # マーカーの半分の幅 (1.0で画面いっぱい)
TARGET_WIDTH_SMALL = 0.1
TARGET_WIDTH_LARGE = 0.2

BUTTON_HALF_WIDTH = 0.1

MAX_STEP_COUNT = 180 * 60

TARGET_CHANGE_THRESHOLD = 0.6

MAGENDA = [1.0, 0.0, 0.75]
ORANGE = [1.0, 0.75, 0.0]
LIGHT_BLUE = [0.0, 1.0, 1.0]
BLUE = [0.0, 0.25, 1.0]
DEEP_PURPLE = [0.5, 0.0, 1.0]
BLACK = [0.0, 0.0, 0.0]
WHITE = [1.0, 1.0, 1.0]

TargetColors = [
    MAGENDA,
    ORANGE,
    LIGHT_BLUE,
    BLUE,
    DEEP_PURPLE
]

YES_BUTTON_POS = [-0.9, 0.0]
NO_BUTTON_POS = [0.9, 0.0]


class AnswerBoxHit(object):
    NONE = 0
    YES = 1
    NO = 2


class Grid(object):
    """def __new__(cls):
        self = super.__new__(cls)
        return self"""

    def __init__(self, center, half_width):
        self.center = center
        self.half_width = half_width


class EightSquareGrid(object):
    side_section = 8
    width = 0.2
    half_width = width/2

    centers_x = [-0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7]
    centers_y = [-0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7]

    def __init__(self):
        self.grids = []

        for center_y in self.centers_y:
            for center_x in self.centers_x:
                center = [center_x, center_y]
                grid = Grid(center, self.half_width)
                self.grids.append(grid)

    def get_location(self, i_x, j_y):
        index = j_y * self.side_section + i_x
        return self.grids[index].center

    def get_random_location(self, number):
        samples = random.sample(self.grids, k=number)
        centers = []
        for sample in samples:
            centers.append(sample.center)
        return centers


class ChangeDetectionContent(BaseContent):
    def __init__(self, target_number, max_learning_count, max_interval_count):
        self.quadrants = EightSquareGrid()
        self.target_number = target_number
        self.max_learning_count = max_learning_count
        self.max_interval_count = max_interval_count

        super(ChangeDetectionContent, self).__init__()

    def _init(self):
        start_marker_texture = self._load_texture('start_marker0.png')
        self.plus_sprite = ContentSprite(start_marker_texture, 0.0, 0.0,
                                         PLUS_MARKER_WIDTH)

        e_marker_texture = self._load_texture('general_e0.png')
        box_texture = self._load_texture('white0.png')

        self.textures = [e_marker_texture, box_texture]

        self._prepare_target_sprites()

        self.start_phase = StartPhase(self.plus_sprite)
        self.interval_phase = IntervalPhase(self.max_interval_count)

        self._set_sprites_to_phases()

        self.answer_state = AnswerState(box_texture)

        self.current_phase = self.start_phase

    def _reset(self):
        pass

    def _step(self, local_focus_pos):
        self.current_phase.step()

        done = self.step_count >= (MAX_STEP_COUNT - 1)

        # Caution: for evaluation phase, need_render -> reward -> reset order is sensitive.
        need_render = self.current_phase.need_render(local_focus_pos)
        reward = self.current_phase.reward()

        if need_render:
            if self.current_phase == self.start_phase:
                self.current_phase = self.learning_phase
            elif self.current_phase == self.learning_phase:
                self.current_phase = self.interval_phase
            elif self.current_phase == self.interval_phase:
                self.current_phase = self.evaluation_phase
            elif self.current_phase == self.evaluation_phase:
                self.current_phase = self.start_phase
                self._prepare_target_sprites()
                self._set_sprites_to_phases()

            self.current_phase.reset()

        print('step=%s, phase=%s' % (self.step_count, self.current_phase))

        return reward, done, need_render

    def _render(self):
        self.current_phase.render(self.common_quad_vlist)

    def _prepare_target_sprites(self):
        centers = self.quadrants.get_random_location(self.target_number)

        self.target_sprites = []
        for center in centers:
            texture = random.choice(self.textures)
            color = random.choice(TargetColors)

            sprite = ContentSprite(tex=texture,
                                   pos_x=center[0],
                                   pos_y=center[1],
                                   width=self.quadrants.half_width,
                                   color=color)
            self.target_sprites.append(sprite)

    def _set_sprites_to_phases(self):
        self.learning_phase = LearningPhase(self.target_sprites, self.max_learning_count)

        e_marker_texture = self.textures[0]
        box_texture = self.textures[1]
        self.evaluation_phase = EvaluationPhase(self.target_sprites, box_texture, e_marker_texture)


class AbstractPhase(object):
    def step(self):
        raise NotImplementedError()

    def reset(self):
        raise NotImplementedError()

    def need_render(self, local_focus_pos):
        raise NotImplementedError()

    def reward(self):
        raise NotImplementedError()

    def render(self, common_quad_vlist):
        raise NotImplementedError()


class StartPhase(AbstractPhase):
    def __init__(self, plus_sprite):
        self.plus_sprite = plus_sprite

    def step(self):
        pass

    def reset(self):
        pass

    def need_render(self, local_focus_pos):
        return self.plus_sprite.contains(local_focus_pos)

    def reward(self):
        return 0

    def render(self, common_quad_vlist):
        self.plus_sprite.render(common_quad_vlist)


class LearningPhase(AbstractPhase):
    def __init__(self, target_sprites, max_learning_count):
        self.target_sprites = target_sprites
        self.learning_count = 0
        self.max_learning_count = max_learning_count

    def step(self):
        self.learning_count += 1

    def reset(self):
        self.learning_count = 0

    def need_render(self, local_focus_pos):
        return self.learning_count >= self.max_learning_count

    def reward(self):
        return 0

    def render(self, common_quad_vlist):
        for sprite in self.target_sprites:  # Phase.LEARNING or Phase.EVALUATION
            sprite.render(common_quad_vlist)


class IntervalPhase(AbstractPhase):
    def __init__(self, max_interval_count):
        self.interval_count = 0
        self.max_interval_count = max_interval_count

    def step(self):
        self.interval_count += 1

    def reset(self):
        self.interval_count = 0

    def need_render(self, local_focus_pos):
        return self.interval_count >= self.max_interval_count

    def reward(self):
        return 0

    def render(self, common_quad_vlist):
        pass


class EvaluationPhase(AbstractPhase):
    def __init__(self, target_sprites, box_texture, e_marker_texture):
        self.target_sprites = target_sprites
        self.answer_state = AnswerState(box_texture)
        self.textures = [box_texture, e_marker_texture]

        self.is_changed = False
        self.hit_type = AnswerBoxHit.NONE

    def step(self):
        pass

    def reset(self):
        if np.random.rand() < TARGET_CHANGE_THRESHOLD:
            self.is_changed = False
            return

        self.is_changed = True
        sprite = np.random.choice(self.target_sprites)

        rand_num = np.random.random_integers(0, 2)
        if rand_num == 0:
            self._change_color(sprite)
        elif rand_num == 1:
            self._change_texture(sprite)
        elif rand_num == 2:
            self._change_color(sprite)
            self._change_texture(sprite)

    def need_render(self, local_focus_pos):
        self.hit_type = self.answer_state.detect_hit(local_focus_pos)
        return self.hit_type == AnswerBoxHit.YES or self.hit_type == AnswerBoxHit.NO

    def reward(self):
        reward = 0
        if self.hit_type == AnswerBoxHit.YES and self.is_changed:
            reward = 1
        elif self.hit_type == AnswerBoxHit.NO and not self.is_changed:
            reward = 1

        return reward

    def render(self, common_quad_vlist):
        for sprite in self.target_sprites:  # Phase.LEARNING or Phase.EVALUATION
            sprite.render(common_quad_vlist)

        self.answer_state.render(common_quad_vlist)

    def _change_color(self, sprite):
        next_color = random.choice(TargetColors)
        while next_color == sprite.color:
            next_color = random.choice(TargetColors)

        sprite.color = next_color

    def _change_texture(self, sprite):
        if sprite.tex == self.textures[0]:
            sprite.tex = self.textures[1]
        else:
            sprite.tex = self.textures[0]


class AnswerState(object):
    def __init__(self, texture):
        self.yes_button = AnswerButtonSprite(texture, YES_BUTTON_POS)
        self.no_button = AnswerButtonSprite(texture, NO_BUTTON_POS)

    def detect_hit(self, local_focus_pos):
        if self.yes_button.contains(local_focus_pos):
            return AnswerBoxHit.YES
        elif self.no_button.contains(local_focus_pos):
            return AnswerBoxHit.NO
        else:
            return AnswerBoxHit.NONE

    def render(self, common_quad_vlist):
        self.yes_button.render(common_quad_vlist)
        self.no_button.render(common_quad_vlist)


class AnswerButtonSprite(ContentSprite):
    def __init__(self, texture, position):
        super(ContentSprite, self).__init__()

        self.tex = texture
        self.width = BUTTON_HALF_WIDTH
        self.rot_index = 0
        self.color = BLACK
        self.pos_x = position[0]
        self.pos_y = position[1]
