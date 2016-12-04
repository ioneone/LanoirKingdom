import pygame
from pygame.locals import *
import sys
import os
import random
import struct

SCREEN_RECT = Rect(0, 0, 640, 480)
TILE_SIZE = 32
BAR_SIZE = 50
DOWN, LEFT, RIGHT, UP = 0, 1, 2, 3  # in the order of the image
STOP, AUTO_MOVE, INPUT_MOVE = 0, 1, 2
AUTO_MOVE_RATE = 0.05  # how often NPC moves
ENCOUNTER_RATE = 0.05  # how often the player encounter a monster
SKILL_EFFECT_SIZE = 192

TITLE, FILED, TALK, COMMAND, BATTLE_INIT, BATTLE_COMMAND, BATTLE_PROCESS, STATUS, SHOP, ITEM = range(10)

BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
ORANGE = (243, 152, 0)
DARK_GREEN = (87, 144, 151)
LIGHT_BLUE = (17, 248, 216)

full_screen_flag = False

sounds = {}  # { name: sound file }

game_state = TITLE


def load_image(directory, filename):
    file_path = os.path.join(directory, filename)
    try:
        image = pygame.image.load(file_path).convert_alpha()
    except pygame.error:
        print("Cannot find image", file_path)
        image = None
    return image


def split_image(image, size):
    image_list = []
    width = image.get_rect().width
    height = image.get_rect().height
    row = int(height / size)
    column = int(width / size)
    for r in range(0, row*size, size):
        for c in range(0, column*size, size):
            trimmed_image = pygame.Surface((size, size), pygame.SRCALPHA, 32)
            trimmed_image.blit(image, (0, 0), (c, r, size, size))
            #  The optional flags argument can be set to pygame.RLEACCEL
            #  to provide better performance on non accelerated displays
            #  choose the pixel color at top-left to be transparent
            # trimmed_image.set_colorkey(trimmed_image.get_at((0, 0)), RLEACCEL)
            #  make the image editable
            trimmed_image.convert()
            image_list.append(trimmed_image)
    return image_list


def blend_image(image1, image2, blend_factor):
    # image1 and image2 are the same size
    # blend image2 on image1
    width = image1.get_rect().width
    height = image1.get_rect().height
    surface1 = pygame.Surface((width, height), pygame.SRCALPHA, 32)
    surface1.blit(image1, (0, 0))
    surface2 = pygame.Surface((width, height), pygame.SRCALPHA, 32)
    surface2.blit(image2, (0, 0))
    blend_alpha = int(255 * blend_factor)
    for h in range(height):
        for w in range(width):
            color1 = surface1.get_at((w, h))
            color2 = surface2.get_at((w, h))

            r = color1[0]*(1-blend_factor)+color2[0]*blend_factor
            if r > 255:
                r = 255
            g = color1[1]*(1-blend_factor)+color2[1]*blend_factor
            if g > 255:
                g = 255
            b = color1[2]*(1-blend_factor)+color2[2]*blend_factor
            if b > 255:
                b = 255
            a = color1[3]*(1-blend_factor)+color2[3]*blend_factor
            if a > 255:
                a = 255
            color = (r, g, b, a)
            # print(color)
            surface1.set_at((w, h), color)

    return surface1


class pyRPG:

    def __init__(self):
        pygame.init()
        # DOUBLEBUF
        # using a separate block of memory to apply all the draw routines
        # and then copying that block (buffer) to video memory as a single
        # operation.
        # HWSURFACE
        # using memory on the video card ("hardware") for storing draws
        # as opposed to main memory ("software").
        # The main reason for this is that the bandwidth between main memory
        # and video memory tends to be slow and so being able to draw directly
        # can speed this up
        self.screen = pygame.display.set_mode(SCREEN_RECT.size, DOUBLEBUF | HWSURFACE)
        # self.screen = pygame.display.set_mode(SCREEN_RECT.size, DOUBLEBUF | HWSURFACE | FULLSCREEN)
        pygame.display.set_caption("Lanoir Kingdom")

        self.load_sounds("se")
        self.load_character_chips("data", "charachip.dat")
        self.load_map_chips("data", "mapchip.dat")
        self.load_enemy_batch("data", "enemybatch.dat")
        self.load_items("data", "itemicon.dat")

        self.party = Party()
        player1 = Knight("swordman_female", 4, 4, (3, 5), DOWN, True, self.party)
        player2 = Mage("elf_female2", 4, 4, (3, 4), DOWN, False, self.party)
        player3 = Assassin("priestess", 4, 4, (3, 3), DOWN, False, self.party)
        player4 = Priest("magician_female", 4, 4, (3, 2), DOWN, False, self.party)
        self.party.add(player1)
        self.party.add(player2)
        self.party.add(player3)
        self.party.add(player4)

        self.map = Map("data", "test2", self.party)
        self.message_engine = MessageEngine("data", "lilliput_steps.ttf", 16, WHITE)
        self.message_window = MessageWindow(Rect(140, 334, 360, 140), self.message_engine)
        self.command_window = CommandWindow(Rect(16, 16, 300, 160), self.message_engine)
        self.player_status_window = PlayerStatusWindow(SCREEN_RECT, self.party, self.message_engine)
        self.shop_window = ShopWindow(SCREEN_RECT, self.message_engine)
        self.item_window = ItemWindow(SCREEN_RECT, self.message_engine, self.party)

        self.title = Title(self.message_engine)
        self.battle = Battle(self.message_window, self.message_engine, self.party)

        global game_state
        game_state = TITLE
        self.game_loop()

    def game_loop(self):
        clock = pygame.time.Clock()
        while True:
            clock.tick(60)
            self.input()
            self.update()
            self.draw()
            pygame.display.update()
            self.check_event()

    def input(self):
        global game_state
        if game_state == TITLE:
            self.title.input()
        elif game_state == FILED:
            self.map.input()
            self.party.input(self.map, self.battle)
        elif game_state == TALK:
            self.message_window.update()
        elif game_state == BATTLE_INIT or game_state == BATTLE_COMMAND or game_state == BATTLE_PROCESS:
            self.battle.update()
            self.message_window.update()

    def update(self):
        global game_state
        if game_state == TITLE:
            self.title.update()
        elif game_state == FILED or game_state == TALK or game_state == COMMAND:
            self.map.update()
            self.party.update()
        elif game_state == TALK:
            self.message_window.update()
        elif game_state == STATUS:
            self.player_status_window.update()
        elif game_state == SHOP:
            self.shop_window.update()
        elif game_state == ITEM:
            self.item_window.update()

    def draw(self):
        global game_state
        if game_state == TITLE:
            self.title.draw(self.screen)
        elif game_state == FILED or game_state == TALK or game_state == COMMAND:
            offsets = self.calculate_offsets(self.party.members[0])
            self.map.draw(self.screen, offsets)
            self.party.draw(self.screen, offsets)
            self.message_window.draw(self.screen)
            self.command_window.draw(self.screen)
            self.show_info()
        elif game_state in (BATTLE_INIT, BATTLE_COMMAND, BATTLE_PROCESS):
            self.battle.draw(self.screen)
            self.message_window.draw(self.screen)
        elif game_state == STATUS:
            self.player_status_window.draw(self.screen)
        elif game_state == SHOP:
            self.shop_window.draw(self.screen)
        elif game_state == ITEM:
            self.item_window.draw(self.screen)

    def check_event(self):  # input
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            # change the event handler based on the game state
            global game_state
            if game_state == TITLE:
                self.title_handler(event)
            elif game_state == FILED:
                self.field_handler(event)
            elif game_state == COMMAND:
                self.command_window_handler(event)
            elif game_state == TALK:
                self.talk_handler(event)
            elif game_state == BATTLE_INIT:
                self.battle_init_handler(event)
            elif game_state == BATTLE_COMMAND:
                self.battle_command_handler(event)
            elif game_state == BATTLE_PROCESS:
                self.battle_process_handler(event)
            elif game_state == STATUS:
                self.player_status_window_handler(event)
            elif game_state == SHOP:
                self.shop_window_handler(event)
            elif game_state == ITEM:
                self.item_window_handler(event)

    def item_window_handler(self, event):
        global game_state
        if event.type == KEYDOWN and event.key == K_q:
            sounds["pi"].play()
            # reset everything
            self.item_window.cursor_position = 0
            self.item_window.cursor_is_in = self.item_window.INVENTORY_RECT
            self.item_window.is_grabbing = False
            if self.item_window.selected_item:
                Player.inventory[self.item_window.selected_item_position] = self.item_window.selected_item
                self.item_window.selected_item = None
                self.item_window.selected_item_position = None
            game_state = FILED
        if event.type == KEYDOWN and event.key == K_LEFT:
            if self.item_window.cursor_is_in == self.item_window.INVENTORY_RECT:
                sounds["pi"].play()
                if self.item_window.cursor_position == 0:
                    self.item_window.cursor_is_in = self.item_window.BAG_RECT
                    self.item_window.cursor_position = 4
                elif self.item_window.cursor_position == 5:
                    self.item_window.cursor_is_in = self.item_window.EQUIPMENT_RECT
                    self.item_window.cursor_position = 1
                elif self.item_window.cursor_position == 10 or self.item_window.cursor_position == 15:
                    self.item_window.cursor_is_in = self.item_window.EQUIPMENT_RECT
                    self.item_window.cursor_position = 3
                elif self.item_window.cursor_position == 20:
                    self.item_window.cursor_is_in = self.item_window.EQUIPMENT_RECT
                    self.item_window.cursor_position = 5
                else:
                    self.item_window.cursor_position -= 1
            elif self.item_window.cursor_is_in == self.item_window.DROP_RECT:
                sounds["pi"].play()
                self.item_window.cursor_is_in = self.item_window.INVENTORY_RECT
                self.item_window.cursor_position = 24
            elif self.item_window.cursor_is_in == self.item_window.BAG_RECT:
                if not self.item_window.cursor_position == 0:
                    sounds["pi"].play()
                    self.item_window.cursor_position -= 1
            elif self.item_window.cursor_is_in == self.item_window.EQUIPMENT_RECT:
                if self.item_window.cursor_position == 1 \
                        or self.item_window.cursor_position == 3 \
                        or self.item_window.cursor_position == 5:
                    sounds["pi"].play()
                    self.item_window.cursor_position -= 1

        elif event.type == KEYDOWN and event.key == K_RIGHT:
            if self.item_window.cursor_is_in == self.item_window.INVENTORY_RECT:
                if self.item_window.cursor_position == 4 \
                        or self.item_window.cursor_position == 9 \
                        or self.item_window.cursor_position == 14 \
                        or self.item_window.cursor_position == 19 \
                        or self.item_window.cursor_position == 24:
                    self.item_window.cursor_is_in = self.item_window.DROP_RECT
                    self.item_window.cursor_position = 0
                else:
                    self.item_window.cursor_position += 1
                    sounds["pi"].play()
            elif self.item_window.cursor_is_in == self.item_window.DROP_RECT:
                pass
            elif self.item_window.cursor_is_in == self.item_window.BAG_RECT:
                if self.item_window.cursor_position == 4:
                    self.item_window.cursor_is_in = self.item_window.INVENTORY_RECT
                    self.item_window.cursor_position = 0
                else:
                    self.item_window.cursor_position += 1
                sounds["pi"].play()
            elif self.item_window.cursor_is_in == self.item_window.EQUIPMENT_RECT:
                if self.item_window.cursor_position == 0 \
                        or self.item_window.cursor_position == 2 \
                        or self.item_window.cursor_position == 4:
                    self.item_window.cursor_position += 1
                elif self.item_window.cursor_position == 1:
                    self.item_window.cursor_is_in = self.item_window.INVENTORY_RECT
                    self.item_window.cursor_position = 5
                elif self.item_window.cursor_position == 3:
                    self.item_window.cursor_is_in = self.item_window.INVENTORY_RECT
                    self.item_window.cursor_position = 10
                elif self.item_window.cursor_position == 5:
                    self.item_window.cursor_is_in = self.item_window.INVENTORY_RECT
                    self.item_window.cursor_position = 20
                sounds["pi"].play()

        elif event.type == KEYDOWN and event.key == K_UP:
            if self.item_window.cursor_is_in == self.item_window.INVENTORY_RECT:
                if self.item_window.cursor_position - 5 >= 0:
                    sounds["pi"].play()
                    self.item_window.cursor_position -= 5
            elif self.item_window.cursor_is_in == self.item_window.DROP_RECT:
                pass
            elif self.item_window.cursor_is_in == self.item_window.BAG_RECT:
                pass
            elif self.item_window.cursor_is_in == self.item_window.EQUIPMENT_RECT:
                if self.item_window.cursor_position == 0:
                    self.item_window.cursor_is_in = self.item_window.BAG_RECT
                    self.item_window.cursor_position = 0
                elif self.item_window.cursor_position == 1:
                    self.item_window.cursor_is_in = self.item_window.BAG_RECT
                    self.item_window.cursor_position = 4
                else:
                    self.item_window.cursor_position -= 2
                sounds["pi"].play()

        elif event.type == KEYDOWN and event.key == K_DOWN:
            if self.item_window.cursor_is_in == self.item_window.INVENTORY_RECT:
                if self.item_window.cursor_position + 5 < 25:
                    sounds["pi"].play()
                    self.item_window.cursor_position += 5
            elif self.item_window.cursor_is_in == self.item_window.DROP_RECT:
                pass
            elif self.item_window.cursor_is_in == self.item_window.BAG_RECT:
                if self.item_window.cursor_position == 0 or self.item_window.cursor_position == 1:
                    sounds["pi"].play()
                    self.item_window.cursor_is_in = self.item_window.EQUIPMENT_RECT
                    self.item_window.cursor_position = 0
                elif self.item_window.cursor_position == 3 or self.item_window.cursor_position == 4:
                    sounds["pi"].play()
                    self.item_window.cursor_is_in = self.item_window.EQUIPMENT_RECT
                    self.item_window.cursor_position = 1
            elif self.item_window.cursor_is_in == self.item_window.EQUIPMENT_RECT:
                if self.item_window.cursor_position == 4:
                    pass
                elif self.item_window.cursor_position == 5:
                    pass
                else:
                    sounds["pi"].play()
                    self.item_window.cursor_position += 2

        elif event.type == KEYDOWN and event.key == K_SPACE:
            if self.item_window.cursor_is_in == self.item_window.INVENTORY_RECT:
                if self.item_window.is_grabbing:
                    if not Player.inventory[self.item_window.cursor_position]:
                        Player.inventory[self.item_window.cursor_position] = self.item_window.selected_item
                        self.item_window.selected_item = None
                        self.item_window.selected_item_position = None
                        self.item_window.selected_item_from = None
                        self.item_window.is_grabbing = False
                else:
                    if Player.inventory[self.item_window.cursor_position]:
                        self.item_window.selected_item = Player.inventory[self.item_window.cursor_position]
                        self.item_window.selected_item_position = self.item_window.cursor_position
                        self.item_window.selected_item_from = self.item_window.INVENTORY_RECT
                        Player.inventory[self.item_window.cursor_position] = None
                        self.item_window.is_grabbing = True
            elif self.item_window.cursor_is_in == self.item_window.DROP_RECT:
                if self.item_window.is_grabbing:
                    self.item_window.selected_item = None
                    self.item_window.selected_item_position = None
                    self.item_window.selected_item_from = None
                    self.item_window.is_grabbing = False

            elif self.item_window.cursor_is_in == self.item_window.BAG_RECT:
                if self.item_window.is_grabbing:
                    if not self.item_window.selected_player.bag[self.item_window.cursor_position]:
                        self.item_window.selected_player.bag[self.item_window.cursor_position] = self.item_window.selected_item
                        self.item_window.selected_item = None
                        self.item_window.selected_item_position = None
                        self.item_window.selected_item_from = None
                        self.item_window.is_grabbing = False
                else:
                    if self.item_window.selected_player.bag[self.item_window.cursor_position]:
                        self.item_window.selected_item = self.item_window.selected_player.bag[self.item_window.cursor_position]
                        self.item_window.selected_player.bag[self.item_window.cursor_position] = None
                        self.item_window.selected_item_position = self.item_window.cursor_position
                        self.item_window.selected_item_from = self.item_window.BAG_RECT
                        self.item_window.is_grabbing = True

            elif self.item_window.cursor_is_in == self.item_window.EQUIPMENT_RECT:

                # # equipments
                # self.weapon = None
                # self.head = None
                # self.body = None
                # self.arms = None
                # self.legs = None
                # self.boots = None
                # self.accessory = None

                if self.item_window.cursor_position == 0:  # weapon
                    if self.item_window.is_grabbing:
                        if not self.item_window.selected_player.weapon:
                            self.item_window.selected_player.weapon = self.item_window.selected_item
                            self.item_window.selected_item = None
                            self.item_window.selected_item_position = None
                            self.item_window.selected_item_from = None
                            self.item_window.is_grabbing = False
                    else:
                        if self.item_window.selected_player.weapon:
                            self.item_window.selected_item = self.item_window.selected_player.weapon
                            self.item_window.selected_player.weapon = None
                            self.item_window.selected_item_position = self.item_window.cursor_position
                            self.item_window.selected_item_from = self.item_window.EQUIPMENT_RECT
                            self.item_window.is_grabbing = True

                elif self.item_window.cursor_position == 1:  # head
                    if self.item_window.is_grabbing:
                        if not self.item_window.selected_player.head:
                            self.item_window.selected_player.head = self.item_window.selected_item
                            self.item_window.selected_item = None
                            self.item_window.selected_item_position = None
                            self.item_window.selected_item_from = None
                            self.item_window.is_grabbing = False
                    else:
                        if self.item_window.selected_player.head:
                            self.item_window.selected_item = self.item_window.selected_player.head
                            self.item_window.selected_player.head = None
                            self.item_window.selected_item_position = self.item_window.cursor_position
                            self.item_window.selected_item_from = self.item_window.EQUIPMENT_RECT
                            self.item_window.is_grabbing = True
                elif self.item_window.cursor_position == 2:  # accessory
                    if self.item_window.is_grabbing:
                        if not self.item_window.selected_player.accessory:
                            self.item_window.selected_player.accessory = self.item_window.selected_item
                            self.item_window.selected_item = None
                            self.item_window.selected_item_position = None
                            self.item_window.selected_item_from = None
                            self.item_window.is_grabbing = False
                    else:
                        if self.item_window.selected_player.accessory:
                            self.item_window.selected_item = self.item_window.selected_player.accessory
                            self.item_window.selected_player.accessory = None
                            self.item_window.selected_item_position = self.item_window.cursor_position
                            self.item_window.selected_item_from = self.item_window.EQUIPMENT_RECT
                            self.item_window.is_grabbing = True
                elif self.item_window.cursor_position == 3:  # armor
                    if self.item_window.is_grabbing:
                        if not self.item_window.selected_player.body:
                            self.item_window.selected_player.body = self.item_window.selected_item
                            self.item_window.selected_item = None
                            self.item_window.selected_item_position = None
                            self.item_window.selected_item_from = None
                            self.item_window.is_grabbing = False
                    else:
                        if self.item_window.selected_player.body:
                            self.item_window.selected_item = self.item_window.selected_player.body
                            self.item_window.selected_player.body = None
                            self.item_window.selected_item_position = self.item_window.cursor_position
                            self.item_window.selected_item_from = self.item_window.EQUIPMENT_RECT
                            self.item_window.is_grabbing = True
                elif self.item_window.cursor_position == 4:  # boots
                    if self.item_window.is_grabbing:
                        if not self.item_window.selected_player.boots:
                            self.item_window.selected_player.boots = self.item_window.selected_item
                            self.item_window.selected_item = None
                            self.item_window.selected_item_position = None
                            self.item_window.selected_item_from = None
                            self.item_window.is_grabbing = False
                    else:
                        if self.item_window.selected_player.boots:
                            self.item_window.selected_item = self.item_window.selected_player.boots
                            self.item_window.selected_player.boots = None
                            self.item_window.selected_item_position = self.item_window.cursor_position
                            self.item_window.selected_item_from = self.item_window.EQUIPMENT_RECT
                            self.item_window.is_grabbing = True
                elif self.item_window.cursor_position == 5:  # hand
                    if self.item_window.is_grabbing:
                        if not self.item_window.selected_player.arms:
                            self.item_window.selected_player.arms = self.item_window.selected_item
                            self.item_window.selected_item = None
                            self.item_window.selected_item_position = None
                            self.item_window.selected_item_from = None
                            self.item_window.is_grabbing = False
                    else:
                        if self.item_window.selected_player.arms:
                            self.item_window.selected_item = self.item_window.selected_player.arms
                            self.item_window.selected_player.arms = None
                            self.item_window.selected_item_position = self.item_window.cursor_position
                            self.item_window.selected_item_from = self.item_window.EQUIPMENT_RECT
                            self.item_window.is_grabbing = True

    def shop_window_handler(self, event):
        global game_state
        if event.type == KEYDOWN and event.key == K_q:
            sounds["pi"].play()
            # reset everything
            self.shop_window.selected_item = None
            self.shop_window.is_grabbing = None
            self.shop_window.cursor_position = 0
            self.shop_window.cursor_in_shop_shelf = True
            game_state = FILED
            self.map.play_bgm()
            self.map.play_bgm()
        if event.type == KEYDOWN and event.key == K_UP:
            if not self.shop_window.cursor_in_shop_shelf:
                if self.shop_window.cursor_position - 5 >= 0:
                    sounds["pi"].play()
                    self.shop_window.cursor_position -= 5
            else:
                # if the hand cursor is in the shop shelf
                if self.shop_window.cursor_position - 3 >= 0:
                    sounds["pi"].play()
                    self.shop_window.cursor_position -= 3
        elif event.type == KEYDOWN and event.key == K_DOWN:
            if not self.shop_window.cursor_in_shop_shelf:
                if self.shop_window.cursor_position + 5 < 25:
                    sounds["pi"].play()
                    self.shop_window.cursor_position += 5
            else:
                # if the hand cursor is not in the shop shelf
                if self.shop_window.cursor_position + 3 < 12:
                    sounds["pi"].play()
                    self.shop_window.cursor_position += 3
        elif event.type == KEYDOWN and event.key == K_LEFT:
            if not self.shop_window.cursor_in_shop_shelf:
                if not self.shop_window.cursor_position == 0 \
                        and not self.shop_window.cursor_position == 5 \
                        and not self.shop_window.cursor_position == 10 \
                        and not self.shop_window.cursor_position == 15 \
                        and not self.shop_window.cursor_position == 20:
                    sounds["pi"].play()
                    self.shop_window.cursor_position -= 1
            else:
                # if the hand cursor is in the shop shelf
                if self.shop_window.cursor_position == 0:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 9
                    self.shop_window.cursor_in_shop_shelf = False
                elif self.shop_window.cursor_position == 3:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 14
                    self.shop_window.cursor_in_shop_shelf = False
                elif self.shop_window.cursor_position == 6:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 19
                    self.shop_window.cursor_in_shop_shelf = False
                elif self.shop_window.cursor_position == 9:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 24
                    self.shop_window.cursor_in_shop_shelf = False
                else:
                    sounds["pi"].play()
                    self.shop_window.cursor_position -= 1

        elif event.type == KEYDOWN and event.key == K_RIGHT:
            if not self.shop_window.cursor_in_shop_shelf:
                if self.shop_window.cursor_position == 4 or self.shop_window.cursor_position == 9:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 0
                    self.shop_window.cursor_in_shop_shelf = True
                elif self.shop_window.cursor_position == 14:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 3
                    self.shop_window.cursor_in_shop_shelf = True
                elif self.shop_window.cursor_position == 19:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 6
                    self.shop_window.cursor_in_shop_shelf = True
                elif self.shop_window.cursor_position == 24:
                    sounds["pi"].play()
                    self.shop_window.cursor_position = 9
                    self.shop_window.cursor_in_shop_shelf = True
                else:
                    sounds["pi"].play()
                    self.shop_window.cursor_position += 1
            else:
                # if the hand cursor is in the shop shelf
                if not self.shop_window.cursor_position == 2 \
                        and not self.shop_window.cursor_position == 5 \
                        and not self.shop_window.cursor_position == 8:
                    sounds["pi"].play()
                    self.shop_window.cursor_position += 1

        elif event.type == KEYDOWN and event.key == K_SPACE:
            if self.shop_window.is_grabbing:
                if self.shop_window.cursor_in_shop_shelf:
                    if self.shop_window.is_grabbing_product:
                        sounds["cancel"].play()
                        self.shop_window.is_grabbing = False
                        self.shop_window.is_grabbing_product = None
                        self.shop_window.selected_item_position = None
                    else:
                        if self.shop_window.cursor_position == 9:
                            # sell
                            sounds["cha-ching"].play()
                            self.shop_window.purchase_price = -self.shop_window.selected_item.price
                            self.shop_window.is_grabbing = False
                            self.shop_window.selected_item = None
                            self.shop_window.selected_item_position = None
                            self.shop_window.is_grabbing_product = None
                        else:
                            sounds["cancel"].play()
                            Player.inventory[self.shop_window.selected_item_position] = self.shop_window.selected_item
                            self.shop_window.selected_item = None
                            self.shop_window.selected_item_position = None
                            self.shop_window.is_grabbing = False
                            self.shop_window.is_grabbing_product = None

                else:
                    # if the cursor is in the inventory
                    if not Player.inventory[self.shop_window.cursor_position]:
                        if self.shop_window.is_grabbing_product:
                            # buy
                            if Player.gold - self.shop_window.purchase_price >= self.shop_window.selected_item.price:
                                sounds["cha-ching"].play()
                                self.shop_window.purchase_price = self.shop_window.selected_item.price
                                Player.inventory[self.shop_window.cursor_position] = self.shop_window.selected_item
                                self.shop_window.selected_item = None
                                self.shop_window.selected_item_position = None
                                self.shop_window.is_grabbing = False
                                self.shop_window.is_grabbing_product = None
                            else:
                                sounds["cancel"].play()
                        else:
                            Player.inventory[self.shop_window.cursor_position] = self.shop_window.selected_item
                            self.shop_window.selected_item = None
                            self.shop_window.selected_item_position = None
                            self.shop_window.is_grabbing = False
                            self.shop_window.is_grabbing_product = None

                    else:
                        sounds["cancel"].play()

            else:
                # if not grabbing
                if self.shop_window.cursor_in_shop_shelf:
                    if self.shop_window.cursor_position < len(self.shop_window.items_on_sale):
                        self.shop_window.selected_item = self.shop_window.items_on_sale[self.shop_window.cursor_position]
                        self.shop_window.selected_item_position = self.shop_window.cursor_position
                        self.shop_window.is_grabbing = True
                        self.shop_window.is_grabbing_product = True
                        sounds["pick2"].play()
                else:
                    # if the cursor is in the inventory
                    if Player.inventory[self.shop_window.cursor_position]:
                        sounds["pick2"].play()
                        self.shop_window.selected_item = Player.inventory[self.shop_window.cursor_position]
                        self.shop_window.selected_item_position = self.shop_window.cursor_position
                        Player.inventory[self.shop_window.cursor_position] = None
                        self.shop_window.is_grabbing = True
                        self.shop_window.is_grabbing_product = False

        elif event.type == KEYDOWN and event.key == K_c:
            Player.inventory[0] = Item("agl", "test", 100)

    def battle_command_handler(self, event):
        global game_state
        if event.type == KEYDOWN and event.key == K_UP:
            if self.battle.command_window.command == 0:
                return
            self.battle.command_window.command -= 1
        elif event.type == KEYDOWN and event.key == K_DOWN:
            if self.battle.command_window.command == 3:
                return
            self.battle.command_window.command += 1

        if event.type == KEYDOWN and event.key == K_SPACE:
            sounds["pi"].play()
            if self.battle.command_window.command == BattleCommandWindow.ATTACK:
                self.message_window.set_message("player is attacking the monster")
            elif self.battle.command_window.command == BattleCommandWindow.SPELL:
                self.message_window.set_message("I don't know any spell")
            elif self.battle.command_window.command == BattleCommandWindow.ITEM:
                self.message_window.set_message("I don't have any item")
            elif self.battle.command_window.command == BattleCommandWindow.ESCAPE:
                self.message_window.set_message("Run!")
            self.battle.command_window.hide()
            game_state = BATTLE_PROCESS

    def battle_process_handler(self, event):
        global game_state
        if event.type == KEYDOWN and event.key == K_SPACE:
            self.message_window.hide()
            if self.battle.command_window.command == BattleCommandWindow.ESCAPE:
                self.map.play_bgm()
                game_state = FILED
            elif self.battle.command_window.command == BattleCommandWindow.ATTACK:
                self.battle.skill_effect = self.battle.party.members[0].skills[0]
                self.battle.skill_effect.invoke()
                self.battle.command_window.show()
                game_state = BATTLE_COMMAND
            else:
                self.battle.command_window.show()
                game_state = BATTLE_COMMAND

    def battle_init_handler(self, event):
        if event.type == KEYDOWN and event.key == K_SPACE:
            self.message_window.hide()
            sounds["pi"].play()
            self.battle.command_window.show()
            for battle_status_window in self.battle.battle_status_windows:
                battle_status_window.show()
            global game_state
            game_state = BATTLE_COMMAND

    def title_handler(self, event):

        if event.type == KEYDOWN and event.key == K_UP:
            self.title.menu -= 1
            if self.title.menu < 0:
                self.title.menu = 0
        elif event.type == KEYDOWN and event.key == K_DOWN:
            self.title.menu += 1
            if self.title.menu > 2:
                self.title.menu = 2

        if event.type == KEYDOWN and event.key == K_SPACE:
            sounds["pi"].play()
            if self.title.menu == Title.START:
                global game_state
                game_state = FILED
                self.map.create("data", "test2")
            elif self.title.menu == Title.CONTINUE:
                pass
            elif self.title.menu == Title.EXIT:
                pygame.quit()
                sys.quit()

    def field_handler(self, event):
        if event.type == KEYDOWN and event.key == K_SPACE:
            if not self.party.members[0].moving:
                sounds["pi"].play()
                self.command_window.show()
                global game_state
                game_state = COMMAND

    def command_window_handler(self, event):
        global game_state
        player = self.party.members[0]

        if event.type == KEYDOWN:
            if event.key == K_LEFT:
                if self.command_window.command <= 3:
                    return
                self.command_window.command -= 4
            elif event.key == K_RIGHT:
                if self.command_window.command >= 4:
                    return
                self.command_window.command += 4
            elif event.key == K_UP:
                if self.command_window.command == 0 or self.command_window.command == 4:
                    return
                self.command_window.command -= 1
            elif event.key == K_DOWN:
                if self.command_window.command == 3 or self.command_window.command == 7:
                    return
                self.command_window.command += 1

            if event.key == K_SPACE:
                if self.command_window.command == CommandWindow.TALK:
                    sounds["pi"].play()
                    self.command_window.hide()
                    character = player.talk(self.map)
                    if character:
                        if isinstance(character, Clerk):
                            self.shop_window.set_clerk(character)
                            game_state = SHOP
                            self.shop_window.play_bgm()
                        else:
                            self.message_window.set_message(character.message)
                            game_state = TALK
                    else:
                        self.message_window.set_message("There's no one there")
                        game_state = TALK
                elif self.command_window.command == CommandWindow.STATUS:
                    sounds["pi"].play()
                    self.command_window.hide()
                    self.player_status_window.show()
                    game_state = STATUS
                    self.player_status_window.play_bgm()
                elif self.command_window.command == CommandWindow.EQUIPMENT:
                    sounds["pi"].play()
                    self.command_window.hide()
                    self.message_window.set_message("should show the equipment of the player")
                    game_state = TALK
                elif self.command_window.command == CommandWindow.DOOR:
                    sounds["pi"].play()
                    self.command_window.hide()
                    door = player.open(self.map)
                    if door:
                        door.open()
                        self.map.remove_event(door)
                        game_state = FILED
                    else:
                        self.message_window.set_message("There's no door there")
                        game_state = TALK
                elif self.command_window.command == CommandWindow.SPELL:
                    sounds["pi"].play()
                    self.command_window.hide()
                    self.message_window.set_message("Should open a window for spells")
                    game_state = TALK
                elif self.command_window.command == CommandWindow.ITEM:
                    sounds["pi"].play()
                    self.command_window.hide()
                    self.item_window.show()
                    game_state = ITEM
                elif self.command_window.command == CommandWindow.SEARCH:
                    sounds["pi"].play()
                    self.command_window.hide()
                    treasure = player.search(self.map)
                    if treasure:
                        treasure.open()
                        self.message_window.set_message("get "+treasure.item)
                        game_state = TALK
                        self.map.remove_event(treasure)
                    else:
                        self.message_window.set_message("didn't find anything")
                        game_state = TALK

    def talk_handler(self, event):
        if event.type == KEYDOWN and event.key == K_SPACE:
            if not self.message_window.next():
                global game_state
                game_state = FILED

    def player_status_window_handler(self, event):
        # Author: Junhong Wang
        # Date: 2016/11/11
        # Description: input handler for event window
        if event.type == KEYDOWN and event.key == K_d:
            if not self.player_status_window.page + 1 >= len(self.party.members) and not self.player_status_window.points_distribution_flag:
                sounds["pi"].play()
                self.player_status_window.page += 1
        elif event.type == KEYDOWN and event.key == K_a:
            if not self.player_status_window.page - 1 < 0 and not self.player_status_window.points_distribution_flag:
                sounds["pi"].play()
                self.player_status_window.page -= 1
        elif event.type == KEYDOWN and event.key == K_q:
            sounds["pi"].play()
            if self.player_status_window.points_distribution_flag:
                self.player_status_window.points_distribution_flag = False
                self.player_status_window.status_cursor_position = 0
            else:
                self.player_status_window.selection = self.player_status_window.STATUS_WINDOW
                self.player_status_window.page = 0
                global game_state
                game_state = FILED
                self.map.play_bgm()
        elif event.type == KEYDOWN and event.key == K_LEFT:
            if not self.player_status_window.selection == self.player_status_window.STATUS_WINDOW \
                    and not self.player_status_window.points_distribution_flag:
                sounds["pi"].play()
                self.player_status_window.selection = self.player_status_window.STATUS_WINDOW
            elif self.player_status_window.points_distribution_flag and self.player_status_window.selection \
                    == self.player_status_window.STATUS_WINDOW:
                if self.player_status_window.status_after[self.player_status_window.status_cursor_position] - 1 \
                        >= self.player_status_window.status_before[self.player_status_window.status_cursor_position]:
                    sounds["pi"].play()
                    self.player_status_window.status_after[self.player_status_window.status_cursor_position] -= 1
                    self.player_status_window.selected_player.status_points += 1
        elif event.type == KEYDOWN and event.key == K_RIGHT:
            if not self.player_status_window.selection == self.player_status_window.SKILLS_WINDOW \
                    and not self.player_status_window.points_distribution_flag:
                sounds["pi"].play()
                self.player_status_window.selection = self.player_status_window.SKILLS_WINDOW
            elif self.player_status_window.points_distribution_flag and self.player_status_window.selection \
                    == self.player_status_window.STATUS_WINDOW:
                if self.player_status_window.selected_player.status_points > 0:
                    sounds["pi"].play()
                    self.player_status_window.status_after[self.player_status_window.status_cursor_position] += 1
                    self.player_status_window.selected_player.status_points -= 1
        elif event.type == KEYDOWN and event.key == K_SPACE:
            sounds["pi"].play()
            if self.player_status_window.points_distribution_flag:
                # hp, atk, int, de, mgr, agi, cri, exe
                self.player_status_window.selected_player.health = self.player_status_window.status_after[0]
                self.player_status_window.selected_player.attack = self.player_status_window.status_after[1]
                self.player_status_window.selected_player.intelligence = self.player_status_window.status_after[2]
                self.player_status_window.selected_player.defence = self.player_status_window.status_after[3]
                self.player_status_window.selected_player.magic_resistance = self.player_status_window.status_after[4]
                self.player_status_window.selected_player.agility = self.player_status_window.status_after[5]
                self.player_status_window.selected_player.critical_hit = self.player_status_window.status_after[6]
                self.player_status_window.selected_player.experience = self.player_status_window.status_after[7]
            self.player_status_window.points_distribution_flag = not self.player_status_window.points_distribution_flag
            self.player_status_window.status_cursor_position = 0
        elif event.type == KEYDOWN and event.key == K_UP:
            if self.player_status_window.points_distribution_flag:
                if not self.player_status_window.status_cursor_position - 1 < 0:
                    sounds["pi"].play()
                    self.player_status_window.status_cursor_position -= 1
        elif event.type == KEYDOWN and event.key == K_DOWN:
            if self.player_status_window.points_distribution_flag:
                if self.player_status_window.selection == self.player_status_window.STATUS_WINDOW:
                    if not self.player_status_window.status_cursor_position + 1 >= len(self.player_status_window.STATUS):
                        sounds["pi"].play()
                        self.player_status_window.status_cursor_position += 1
                elif self.player_status_window.selection == self.player_status_window.SKILLS_WINDOW:
                    if not self.player_status_window.status_cursor_position + 1 >= len(self.player_status_window.party.members[self.player_status_window.page].skills):
                        sounds["pi"].play()
                        self.player_status_window.status_cursor_position += 1

    def calculate_offsets(self, player):
        # calculate the offsets respect to the player position
        # this will be used to convert world coordinates to screen coordinates
        offset_x = player.rect.topleft[0] - SCREEN_RECT.width / 2
        offset_y = player.rect.topleft[1] - SCREEN_RECT.height / 2
        return offset_x, offset_y

    def show_info(self):
        player = self.party.members[0]
        self.message_engine.draw(self.screen, self.map.name.upper(), (450, 10))
        self.message_engine.draw(self.screen, player.name.upper(), (450, 40))
        player_position_info = str(player.x) + ' ' + str(player.y)
        self.message_engine.draw(self.screen, player_position_info, (450, 70))

    def load_items(self, directory, file_name):
        # Author: Junhong Wang
        # Date: 11/19/2016
        # Description: load items and store them in Shop class
        file_path = os.path.join(directory, file_name)
        file = open(file_path)
        for line in file:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            data = line.split(",")
            item_id = int(data[0])
            item_name = data[1]
            item_class = data[2]
            item_power = data[3]
            item_price = int(data[4])
            item_description = data[5]
            if item_class == "Sword":
                Shop.items.append(Sword(item_name, item_description, item_price, item_power))
            elif item_class == "Axe":
                Shop.items.append(Axe(item_name, item_description, item_price, item_power))
        file.close()

    def load_sounds(self, directory):
        sound_file_name_list = os.listdir(directory)
        print(sound_file_name_list)
        if ".DS_Store" in sound_file_name_list:
            sound_file_name_list.remove(".DS_Store")
        for file_name in sound_file_name_list:
            sound_file_path = os.path.join(directory, file_name)
            sounds[file_name[:-4]] = pygame.mixer.Sound(sound_file_path)
            sounds[file_name[:-4]].set_volume(0.01)

    def load_character_chips(self, directory, file_name):
        file_path = os.path.join(directory, file_name)
        file = open(file_path)
        for line in file:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            data = line.split(",")
            character_id = int(data[0])
            character_name = data[1]
            row = int(data[2])
            column = int(data[3])
            Character.images[character_name] = split_image(load_image("charachip", character_name + ".png"), TILE_SIZE)
        file.close()

    def load_map_chips(self, directory, file_name):
        file_path = os.path.join(directory, file_name)
        file = open(file_path)
        for line in file:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            data = line.split(",")
            map_chip_id = int(data[0])
            map_chip_name = data[1]
            movable = int(data[2])
            Map.images.append(load_image("mapchip", map_chip_name + ".png"))
            Map.movable_type.append(movable)
        file.close()

    def load_enemy_batch(self, directory, file_name):
        # id, name, health, attack, intelligence, defence, magic_resistance, agility, critical_hit, experience
        file_path = os.path.join(directory, file_name)
        file = open(file_path)
        for line in file:
            line = line.rstrip()
            if line.startswith('#'):
                continue
            data = line.split(",")
            id = data[0]
            name = data[1]
            health = data[2]
            attack = data[3]
            intelligence = data[4]
            defence = data[5]
            magic_resistance = data[6]
            agility = data[7]
            critical_hit = data[8]
            experience = data[9]
            Map.enemy_batch.append(Enemy(id, name, health, attack, intelligence, defence, magic_resistance, agility, critical_hit, experience))
        file.close()


class Map:

    images = []
    movable_type = []

    enemy_batch = []

    default = 1  # default map chip id

    def __init__(self, directory, name, party):
        self.name = name
        self.row = 0
        self.column = 0
        self.map = []
        self.characters = []
        self.enemies = []
        self.events = []
        self.bgm_file_path = None
        self.party = party
        self.load(directory)
        self.load_event(directory)

    def create(self, directory, destination_map):
        self.name = destination_map
        self.characters = []
        self.enemies = []
        self.events = []
        self.load(directory)
        self.load_event(directory)

    def input(self):
        for character in self.characters:
            character.input(self)

    def update(self):
        for character in self.characters:
            character.update()

    def draw(self, screen, offsets):
        offset_x, offset_y = offsets
        #  calculate which parts of the map should be drawn (camera culling)
        start_x = int(offset_x / TILE_SIZE) - 1
        end_x = start_x + int(SCREEN_RECT.width/TILE_SIZE) + 2
        start_y = int(offset_y / TILE_SIZE) - 1
        end_y = start_y + int(SCREEN_RECT.height/TILE_SIZE) + 2
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if x < 0 or y < 0 or x > self.column-1 or y > self.row-1:
                    screen.blit(self.images[self.default], (x*TILE_SIZE-offset_x, y*TILE_SIZE-offset_y))
                else:
                    screen.blit(self.images[self.map[y][x]], (x*TILE_SIZE-offset_x, y*TILE_SIZE-offset_y))

        for event in self.events:
            event.draw(screen, offsets)

        for character in self.characters:
            character.draw(screen, offsets)

    def is_movable(self, x, y):
        if x < 0 or x > self.column - 1 or y < 0 or y > self.row - 1:
            return False
        if self.movable_type[self.map[y][x]] == 0:
            return False
        for character in self.characters:
            if character.x == x and character.y == y:
                return False
        for event in self.events:
            if self.movable_type[event.map_chip_id] == 0:
                if event.x == x and event.y == y:
                    return False

        player = self.party.members[0]
        if player.x == x and player.y == y:
            return False

        return True

    def load_event(self, directory):
        file_path = os.path.join(directory, self.name+".evt")
        file = open(file_path)
        for line in file:
            line = line.rstrip()  # remove new line
            if line.startswith("#"):
                continue  # ignore comment line
            data = line.split(",")
            event_type = data[0]
            if event_type == "CHARACTER":
                self.create_character(data)
            elif event_type == "MOVE":
                self.create_move_event(data)
            elif event_type == "BGM":  # background music
                self.play_bgm(data)
            elif event_type == "TREASURE":
                self.create_treasure_event(data)
            elif event_type == "DOOR":
                self.create_door_event(data)
            elif event_type == "OBJECT":
                self.create_object_event(data)
            elif event_type == "Enemy":
                self.create_enemy(data)
            elif event_type == "CLERK":
                self.create_clerk_event(data)
        file.close()

    def play_bgm(self, data=None):

        if data:
            bgm_file_name = data[1]+".ogg"
            self.bgm_file_path = os.path.join("bgm", bgm_file_name)
            pygame.mixer.music.load(self.bgm_file_path)
            pygame.mixer.music.play(-1)  # loop
        else:
            pygame.mixer.music.load(self.bgm_file_path)
            pygame.mixer.music.play(-1)

    def create_treasure_event(self, data):
        x, y = int(data[1]), int(data[2])
        item = data[3]
        treasure = Treasure((x, y), item)
        self.events.append(treasure)

    def create_door_event(self, data):
        x, y = int(data[1]), int(data[2])
        door = Door((x, y))
        self.events.append(door)

    def create_object_event(self, data):
        x, y = int(data[1]), int(data[2])
        map_chip_id = int(data[3])
        object = Object((x, y), map_chip_id)
        self.events.append(object)

    def create_move_event(self, data):
        x, y = int(data[1]), int(data[2])
        map_chip = int(data[3])
        destination_map = data[4]
        destination_x, destination_y = int(data[5]), int(data[6])
        move_event = MoveEvent((x, y), map_chip, destination_map, (destination_x, destination_y))
        self.events.append(move_event)

    def create_character(self, data):
        name = data[1]
        row, column = int(data[2]), int(data[3])
        x, y = int(data[4]), int(data[5])
        direction = int(data[6])
        move_type = int(data[7])
        message = data[8]
        character = Character(name, row, column, (x, y), direction, move_type, message)
        self.characters.append(character)

    def create_clerk_event(self, data):
        name = data[1]
        row, column = int(data[2]), int(data[3])
        x, y = int(data[4]), int(data[5])
        direction = int(data[6])
        move_type = int(data[7])
        message = data[8]
        shop = Shop(data[9])
        clerk = Clerk(name, row, column, (x, y), direction, move_type, message, shop)
        self.characters.append(clerk)

    def create_enemy(self, data):
        id = int(data[1])
        level = int(data[2])
        enemy = self.enemy_batch[id]
        enemy.set_level(level)
        self.enemies.append(enemy)

    def get_character(self, x, y):
        for character in self.characters:
            if character.x == x and character.y == y:
                return character
        return None

    def get_event(self, x, y):
        for event in self.events:
            if event.x == x and event.y == y:
                return event
        return None

    def load(self, directory):
        file_path = os.path.join(directory, self.name+".map")
        file = open(file_path, "rb")  # open with binary format
        self.row = struct.unpack("i", file.read(struct.calcsize("i")))[0]
        self.column = struct.unpack("i", file.read(struct.calcsize("i")))[0]
        self.default = struct.unpack("B", file.read(struct.calcsize("B")))[0]

        self.map = [[4 for c in range(self.column)] for r in range(self.row)]
        for r in range(self.row):
            for c in range(self.column):
                self.map[r][c] = struct.unpack("B", file.read(struct.calcsize("B")))[0]
        file.close()

    def remove_event(self, event):
        self.events.remove(event)


class Character:
    speed = 4  # [pixel per frame], should be factor of 36
    animation_cycle = 24  # the less, the faster
    frame = 0
    images = {}

    def __init__(self, name, row, column, position, direction, move_type, message):
        self.name = name
        self.row = row
        self.column = column
        self.image = self.images[name][0]
        self.x, self.y = position[0], position[1]
        self.rect = self.image.get_rect(topleft=(self.x*TILE_SIZE, self.y*TILE_SIZE))
        self.velocity_x, self.velocity_y = 0, 0
        self.moving = False
        self.direction = direction
        self.move_type = move_type
        self.message = message

    def input(self, map):
        if self.moving:
            #  if the player is between the tiles, let it finish moving
            self.rect.move_ip(self.velocity_x, self.velocity_y)
            if self.rect.left % TILE_SIZE == 0 and self.rect.top % TILE_SIZE == 0:
                self.moving = False
                self.x = int(self.rect.left / TILE_SIZE)
                self.y = int(self.rect.top / TILE_SIZE)
            else:
                return

        if self.move_type == AUTO_MOVE and random.random() < AUTO_MOVE_RATE:
            self.direction = random.randint(0, 3)
            if self.direction == DOWN:
                if map.is_movable(self.x, self.y+1):
                    self.velocity_x, self.velocity_y = 0, self.speed
                    self.moving = True
            elif self.direction == LEFT:
                if map.is_movable(self.x-1, self.y):
                    self.velocity_x, self.velocity_y = -self.speed, 0
                    self.moving = True
            elif self.direction == RIGHT:
                if map.is_movable(self.x+1, self.y):
                    self.velocity_x, self.velocity_y = self.speed, 0
                    self.moving = True
            elif self.direction == UP:
                if map.is_movable(self.x, self.y-1):
                    self.velocity_x, self.velocity_y = 0, -self.speed
                    self.moving = True

    def update(self):
        self.frame += 1
        #  animation
        self.image = self.images[self.name][self.direction*self.column + int(self.frame/self.animation_cycle) % self.column]

    def draw(self, screen, offsets):
        offset_x, offset_y = offsets
        position_x, position_y = self.rect.topleft[0], self.rect.topleft[1]
        screen.blit(self.image, (position_x-offset_x, position_y-offset_y))

    def set_position(self, x, y, direction):
        self.x, self.y = x, y
        self.rect = self.image.get_rect(topleft=(self.x*TILE_SIZE, self.y*TILE_SIZE))
        self.direction = direction


class Item:
    # Author: Junhong Wang
    # Date: 2016/11/19
    # Description: none
    def __init__(self, name, description, price):
        self.name = name
        self.description = description
        self.price = price
        self.image = load_image("itemicon", name+".png")


class Sword(Item):

    def __init__(self, name, description, price, attack):
        Item.__init__(self, name, description, price)
        self.attack = attack



class Armor(Item):
    def __init__(self, name, description, price, defence):
        Item.__init__(self, name, description, price)
        self.defence = defence


class Axe(Item):

    def __init__(self, name, description, price, attack):
        Item.__init__(self, name, description, price)
        self.attack = attack


class Lance(Item):

    def __init__(self, name, description, price, attack):
        Item.__init__(self, name, description, price)
        self.attack = attack


class Cane(Item):

    def __init__(self, name, description, price, intelligence):
        Item.__init__(self, name, description, price)
        self.intelligence = intelligence


class Helmet(Item):

    def __init__(self, name, description, price, defence):
        Item.__init__(self, name, description, price)
        self.defence = defence


class Shoes(Item):

    def __init__(self, name, description, price, defence):
        Item.__init__(self, name, description, price)
        self.defence = defence


class Gloves(Item):

    def __init__(self, name, description, price, defence):
        Item.__init__(self, name, description, price)
        self.defence = defence


class Accessory(Item):

    def __init__(self, name, description, price, defence):
        Item.__init__(self, name, description, price)
        self.defence = defence


class Player(Character):

    inventory = [None] * 25
    gold = 500

    def __init__(self, name, row, column, position, direction, is_leader, party):
        Character.__init__(self, name, row, column, position, direction, INPUT_MOVE, None)
        self.is_leader = is_leader
        self.party = party
        self.bag = [None] * 5

    def input(self, map, battle):
        if self.moving:
            #  if the player is between the tiles, let it finish moving
            self.rect.move_ip(self.velocity_x, self.velocity_y)
            if self.rect.left % TILE_SIZE == 0 and self.rect.top % TILE_SIZE == 0:
                self.moving = False
                self.x = int(self.rect.left / TILE_SIZE)
                self.y = int(self.rect.top / TILE_SIZE)

                if not self.is_leader:
                    return

                event = map.get_event(self.x, self.y)
                if isinstance(event, MoveEvent):
                    sounds["step"].play()
                    destination_map = event.destination_map
                    destination_x = event.destination_x
                    destination_y = event.destination_y
                    map.create("data", destination_map)
                    for player in self.party.members:
                        player.set_position(destination_x, destination_y, DOWN)
                        player.moving = False

                # check enemies
                if map.name == "test2" and random.random() < ENCOUNTER_RATE:
                    global game_state
                    game_state = BATTLE_INIT
                    battle.start(map)

            else:
                return

    def talk(self, map):
        next_x, next_y = self.x, self.y
        if self.direction == DOWN:
            next_y += 1
            event = map.get_event(next_x, next_y)
            if isinstance(event, Object) and event.map_chip_id == 41:
                next_y += 1
        elif self.direction == LEFT:
            next_x -= 1
            event = map.get_event(next_x, next_y)
            if isinstance(event, Object) and event.map_chip_id == 41:
                next_x -= 1
        elif self.direction == RIGHT:
            next_x += 1
            event = map.get_event(next_x, next_y)
            if isinstance(event, Object) and event.map_chip_id == 41:
                next_x += 1
        elif self.direction == UP:
            next_y -= 1
            event = map.get_event(next_x, next_y)
            if isinstance(event, Object) and event.map_chip_id == 41:
                next_y -= 1
        character = map.get_character(next_x, next_y)
        if character:
            if not character.moving:
                if self.direction == DOWN:
                    character.direction = UP
                elif self.direction == LEFT:
                    character.direction = RIGHT
                elif self.direction == RIGHT:
                    character.direction = LEFT
                elif self.direction == UP:
                    character.direction = DOWN
                character.update()
                return character
            return None
        return None

    def search(self, map):
        event = map.get_event(self.x, self.y)
        if isinstance(event, Treasure):
            return event
        return None

    def open(self, map):
        next_x, next_y = self.x, self.y
        if self.direction == DOWN:
            next_y += 1
        elif self.direction == LEFT:
            next_x -= 1
        elif self.direction == RIGHT:
            next_x += 1
        elif self.direction == UP:
            next_y -= 1
        event = map.get_event(next_x, next_y)
        if isinstance(event, Door):
            return event
        return None

    def move_to(self, destination_x, destination_y):
        dx = destination_x - self.x
        dy = destination_y - self.y

        if dx == 1:
            self.direction = RIGHT
        elif dx == -1:

            self.direction = LEFT
        elif dy == -1:
            self.direction = UP
        elif dy == 1:
            self.direction = DOWN

        self.velocity_x, self.velocity_y = dx*self.speed, dy*self.speed
        self.moving = True



class Window:
    EDGE_WIDTH = 4

    def __init__(self, rect):
        self.rect = rect
        #  Returns a new rectangle with the size changed by the given offset.
        #  The rectangle remains centered around its current center.
        #  Negative values will shrink the rectangle.
        self.inner_rect = self.rect.inflate(-self.EDGE_WIDTH*2, -self.EDGE_WIDTH*2)
        self.is_visible = False

    def draw(self, screen):
        if not self.is_visible:
            return
        pygame.draw.rect(screen, WHITE, self.rect, 0)
        pygame.draw.rect(screen, BLACK, self.inner_rect, 0)

    def show(self):
        self.is_visible = True

    def hide(self):
        self.is_visible = False


class MessageEngine:

    def __init__(self, directory, font_file, size, color):
        font_file_path = os.path.join(directory, font_file)
        self.font_file_path = font_file_path
        self.font = pygame.font.Font(font_file_path, size)
        self.color = color
        self.font_width = self.font.size(' ')[0]
        self.font_height = self.font.size(' ')[1]
        print(self.font_width, self.font_height)

    def draw(self, screen, message, position):
        text_rect = self.font.render(message, True, self.color)
        screen.blit(text_rect, position)

    def draw_center(self, screen, message, rect):
        # Author: Junhong
        # Date: 2016/11/12
        # Description: draw the string at the center of given rect
        text_rect = self.font.render(message, True, self.color)
        text_width = text_rect.get_rect().width
        text_height = text_rect.get_rect().height
        screen.blit(text_rect, (rect.centerx-text_width/2, rect.centery-text_height/2))

    def set_color(self, color):
        self.color = color

    def set_size(self, size):
        self.font = pygame.font.Font(self.font_file_path, size)
        self.font_width = self.font.size(' ')[0]
        self.font_height = self.font.size(' ')[1]


class MessageWindow(Window):
    #  should be dynamic
    MAX_CHARS_PER_LINE = 20
    MAX_LINES_PER_PAGE = 3
    MAX_CHARS_PER_PAGE = MAX_CHARS_PER_LINE*MAX_LINES_PER_PAGE
    MAX_LINES = 30
    LINE_HEIGHT = 8  # the width between lines
    animation_cycle = 24

    def __init__(self, rect, message_engine):
        Window.__init__(self, rect)
        self.text_rect = self.inner_rect.inflate(-32, -32)
        self.text = []
        self.current_page = 0
        self.current_position = 0
        self.next_flag = False
        self.hide_flag = False
        self.message_engine = message_engine
        self.cursor = load_image("data", "cursor.png")
        self.frame = 0

    def set_message(self, message):
        self.current_page = 0
        self.current_position = 0
        self.next_flag = False
        self.hide_flag = False
        self.text = [' '] * (self.MAX_LINES*self.MAX_CHARS_PER_LINE)
        pointer = 0  # keep track of the position for the next character
        for i in range(len(message)):
            char = message[i]
            if char == "/":  # new line
                self.text[pointer] = "/"
                pointer += self.MAX_CHARS_PER_LINE
                pointer = int(pointer/self.MAX_CHARS_PER_LINE)*self.MAX_CHARS_PER_LINE
            elif char == "%":  # new page
                self.text[pointer] = "%"
                pointer += self.MAX_CHARS_PER_PAGE
                pointer = int(pointer/self.MAX_CHARS_PER_PAGE)*self.MAX_CHARS_PER_PAGE
            else:
                self.text[pointer] = char
                pointer += 1
        self.text[pointer] = "$"
        self.show()

    def update(self):
        if self.is_visible:
            if not self.next_flag:
                self.current_position += 1
                pointer = self.current_page * self.MAX_CHARS_PER_PAGE + self.current_position
                if self.text[pointer] == "/":
                    self.current_position += self.MAX_CHARS_PER_LINE
                    self.current_position = int(self.current_position/self.MAX_CHARS_PER_LINE) * self.MAX_CHARS_PER_LINE
                elif self.text[pointer] == "%":
                    self.current_position += self.MAX_CHARS_PER_PAGE
                    self.current_position = int(self.current_position/self.MAX_CHARS_PER_PAGE) * self.MAX_CHARS_PER_PAGE
                elif self.text[pointer] == "$":
                    self.hide_flag = True
                if self.current_position % self.MAX_CHARS_PER_PAGE == 0:
                    self.next_flag = True
        self.frame += 1

    def draw(self, screen):
        #  maybe there's a better way to draw it
        Window.draw(self, screen)
        if not self.is_visible:
            return
        for i in range(self.current_position):
            char = self.text[self.current_page*self.MAX_CHARS_PER_PAGE+i]
            if char == "/" or char == "%" or char == "$":
                continue
            dx = self.text_rect[0] + self.message_engine.font_width*(i % self.MAX_CHARS_PER_LINE)
            dy = self.text_rect[1] + (self.LINE_HEIGHT+self.message_engine.font_height) * int(i / self.MAX_CHARS_PER_LINE)
            self.message_engine.draw(screen, char, (dx, dy))
        if (not self.hide_flag) and self.next_flag:
            if int(self.frame / self.animation_cycle) % 2 == 0:
                dx = self.text_rect[0] + (self.MAX_CHARS_PER_LINE / 2) * self.message_engine.font_width - self.message_engine.font_width / 2
                dy = self.text_rect[1] + (self.LINE_HEIGHT + self.message_engine.font_height) * 3
                screen.blit(self.cursor, (dx, dy))

    def next(self):
        if self.hide_flag:
            self.hide()
        if self.next_flag:
            self.current_page += 1
            self.current_position = 0
            self.next_flag = False


# These should all inherit from Event class, which I haven't created.
class MoveEvent:

    def __init__(self, position, map_chip_id, destination_map, destination_position):
        self.x, self.y = position[0], position[1]
        self.map_chip_id = map_chip_id
        self.destination_map = destination_map
        self.destination_x, self.destination_y = destination_position[0], destination_position[1]
        self.image = Map.images[self.map_chip_id]
        self.rect = self.image.get_rect(topleft=(self.x*TILE_SIZE, self.y*TILE_SIZE))

    def draw(self, screen, offsets):
        offset_x, offset_y = offsets
        position_x = self.rect.topleft[0]
        position_y = self.rect.topleft[1]
        screen.blit(self.image, (position_x-offset_x, position_y-offset_y))


class Treasure:

    def __init__(self, position, item):
        self.x, self.y = position[0], position[1]
        self.map_chip_id = 46
        self.image = Map.images[self.map_chip_id]
        self.rect = self.image.get_rect(topleft=(self.x*TILE_SIZE, self.y*TILE_SIZE))
        self.item = item

    def open(self):
        sounds["treasure"].play()

    def draw(self, screen, offsets):
        offset_x, offset_y = offsets
        position_x = self.rect.topleft[0]
        position_y = self.rect.topleft[1]
        screen.blit(self.image, (position_x-offset_x, position_y-offset_y))


class Door:

    def __init__(self, position):
        self.x, self.y = position[0], position[1]
        self.map_chip_id = 45
        self.image = Map.images[self.map_chip_id]
        self.rect = self.image.get_rect(topleft=(self.x*TILE_SIZE, self.y*TILE_SIZE))

    def open(self):
        sounds["door"].play()

    def draw(self, screen, offsets):
        offset_x, offset_y = offsets
        position_x, position_y = self.rect.topleft[0], self.rect.topleft[1]
        screen.blit(self.image, (position_x-offset_x, position_y-offset_y))


class Object:

    def __init__(self, position, map_chip_id):
        self.x, self.y = position[0], position[1]
        self.map_chip_id = map_chip_id
        self.image = Map.images[self.map_chip_id]
        self.rect = self.image.get_rect(topleft=(self.x*TILE_SIZE, self.y*TILE_SIZE))

    def draw(self, screen, offsets):
        offset_x, offset_y = offsets
        position_x, position_y = self.rect.topleft[0], self.rect.topleft[1]
        screen.blit(self.image, (position_x-offset_x, position_y-offset_y))


class CommandWindow(Window):
    LINE_HEIGHT = 8
    MAX_WORDS = 9
    TALK, STATUS, EQUIPMENT, DOOR, SPELL, ITEM, TACTICS, SEARCH = range(0, 8)
    COMMAND = ["TALK", "STATUS", "EQUIPMENT", "DOOR",
               "SPELL", "ITEM", "TACTICS", "SEARCH"]

    def __init__(self, rect, message_engine):
        Window.__init__(self, rect)
        self.text_rect = self.inner_rect.inflate(-32, -32)
        self.command = self.TALK
        self.message_engine = message_engine
        self.cursor = load_image("data", "cursor2.png")
        self.frame = 0

    def draw(self, screen):
        Window.draw(self, screen)
        if not self.is_visible:
            return
        for i in range(0, 4):
            dx = self.text_rect[0] + (self.message_engine.font_width*2)
            dy = self.text_rect[1] + (self.LINE_HEIGHT+self.message_engine.font_height) * (i % 4)
            self.message_engine.draw(screen, self.COMMAND[i], (dx, dy))
        for i in range(4, 8):
            dx = self.text_rect[0] + self.message_engine.font_width * (self.MAX_WORDS+4)
            dy = self.text_rect[1] + (self.LINE_HEIGHT+self.message_engine.font_height) * (i % 4)
            self.message_engine.draw(screen, self.COMMAND[i], (dx, dy))

        dx = self.text_rect[0] + self.message_engine.font_width * (self.MAX_WORDS+2) * int(self.command / 4)
        dy = self.text_rect[1] + (self.LINE_HEIGHT + self.message_engine.font_height) * (self.command % 4)
        screen.blit(self.cursor, (dx, dy))

    def show(self):
        self.command = self.TALK
        self.is_visible = True


class Party:

    def __init__(self):
        self.members = []

    def add(self, player):
        self.members.append(player)

    def input(self, map, battle):
        for player in self.members:
            player.input(map, battle)

        if not self.members[0].moving:
            pressed_keys = pygame.key.get_pressed()
            if pressed_keys[K_DOWN]:
                self.members[0].direction = DOWN
                if map.is_movable(self.members[0].x, self.members[0].y + 1):
                    for i in range(len(self.members) - 1, 0, -1):
                        self.members[i].move_to(self.members[i - 1].x, self.members[i - 1].y)
                    self.members[0].move_to(self.members[0].x, self.members[0].y + 1)
            elif pressed_keys[K_LEFT]:
                self.members[0].direction = LEFT
                if map.is_movable(self.members[0].x - 1, self.members[0].y):
                    for i in range(len(self.members) - 1, 0, -1):
                        self.members[i].move_to(self.members[i - 1].x, self.members[i - 1].y)
                    self.members[0].move_to(self.members[0].x - 1, self.members[0].y)
            elif pressed_keys[K_RIGHT]:
                self.members[0].direction = RIGHT
                if map.is_movable(self.members[0].x + 1, self.members[0].y):
                    for i in range(len(self.members) - 1, 0, -1):
                        self.members[i].move_to(self.members[i - 1].x, self.members[i - 1].y)
                    self.members[0].move_to(self.members[0].x + 1, self.members[0].y)
            elif pressed_keys[K_UP]:
                self.members[0].direction = UP
                if map.is_movable(self.members[0].x, self.members[0].y - 1):
                    for i in range(len(self.members) - 1, 0, -1):
                        self.members[i].move_to(self.members[i - 1].x, self.members[i - 1].y)
                    self.members[0].move_to(self.members[0].x, self.members[0].y - 1)

    def update(self):
        for player in self.members:
            player.update()

    def draw(self, screen, offsets):
        # draw players from the last player
        for player in self.members[::-1]:
            player.draw(screen, offsets)


class Title:

    START, CONTINUE, EXIT = 0, 1, 2

    def __init__(self, message_engine):
        self.message_enigne = message_engine
        self.title_imgage = load_image("data", "title.png")
        self.cursor_image = load_image("data", "title_cursor.png")
        self.logo_image = load_image("data", "logo2.png")
        self.background_image = load_image("data", "sky.png")
        self.menu = self.START
        self.play_bgm()

    def input(self):
        pass

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 128))
        screen.blit(self.background_image, (0, 0))
        screen.blit(self.title_imgage, (0, -100))
        screen.blit(self.logo_image, (250, 430))

        self.message_enigne.set_color(BLACK)
        self.message_enigne.set_size(20)
        self.message_enigne.draw(screen, "START", (260, 300))
        self.message_enigne.draw(screen, "CONTINUE", (260, 340))
        self.message_enigne.draw(screen, "EXIT", (260, 380))
        self.message_enigne.set_size(16)
        self.message_enigne.draw(screen, "2016 Laney Coding Club", (170, 410))
        self.message_enigne.set_color(WHITE)

        if self.menu == self.START:
            screen.blit(self.cursor_image, (240, 300))
        elif self.menu == self.CONTINUE:
            screen.blit(self.cursor_image, (240, 340))
        elif self.menu == self.EXIT:
            screen.blit(self.cursor_image, (240, 380))

    def play_bgm(self):
        bgm_file_name = "title.ogg"
        bgm_file_path = os.path.join("bgm", bgm_file_name)
        pygame.mixer.music.load(bgm_file_path)
        pygame.mixer.music.set_volume(0.01)
        pygame.mixer.music.play(-1)


class Battle:

    images = []

    def __init__(self, message_window, message_engine, party):
        self.message_window = message_window
        self.message_engine = message_engine
        self.command_window = BattleCommandWindow(Rect(96, 338, 136, 136), self.message_engine)

        self.party = party
        players = []

        for player in self.party.members:
            players.append(player)

        self.battle_status_windows = []

        self.battle_status_windows.append(BattleStatusWindow(50, 12, players[0], self.message_engine))
        self.battle_status_windows.append(BattleStatusWindow(210, 12, players[1], self.message_engine))
        self.battle_status_windows.append(BattleStatusWindow(370, 12, players[2], self.message_engine))
        self.battle_status_windows.append(BattleStatusWindow(520, 12, players[3], self.message_engine))

        self.background_image = load_image("data", "grass.png")
        self.enemy = None

        self.skill_effect = None

    def start(self, map):
        self.command_window.hide()
        for battle_status_window in self.battle_status_windows:
            battle_status_window.hide()

        self.message_window.set_message("encounter an enemy")
        self.play_bgm()

        self.enemy = map.enemies[random.randrange(len(map.enemies))]

    def update(self):
        pass

    def draw(self, screen):
        screen.blit(self.background_image, (0, 0))
        center_rect = self.enemy.image.get_rect(center=SCREEN_RECT.center)
        screen.blit(self.enemy.image, center_rect)
        if self.skill_effect:
            if self.skill_effect.life:
                self.skill_effect.draw(screen)
        self.command_window.draw(screen)
        for battle_status_window in self.battle_status_windows:
            battle_status_window.draw(screen)



        # test
        # image = load_image("skilleffect", "attack1.png")
        # screen.blit(image, (0, 0))


    def play_bgm(self):
        bgm_file_name = "battle.ogg"
        bgm_file_path = os.path.join("bgm", bgm_file_name)
        pygame.mixer.music.load(bgm_file_path)
        pygame.mixer.music.play(-1)


class BattleCommandWindow(Window):
    LINE_HEIGHT = 8
    ATTACK, SPELL, ITEM, ESCAPE = 0, 1, 2, 3
    COMMAND = ["battle", "spell", "item", "run"]

    def __init__(self, rect, message_engine):
        Window.__init__(self, rect)
        self.command = self.ATTACK
        self.text_rect = self.inner_rect.inflate(-32, -16)
        self.message_engine = message_engine
        self.cursor = load_image("data", "cursor2.png")
        self.frame = 0

    def draw(self, screen):
        Window.draw(self, screen)
        if not self.is_visible:
            return

        for i in range(0, 4):
            dx = self.text_rect[0] + self.message_engine.font_width
            dy = self.text_rect[1] + (self.LINE_HEIGHT+self.message_engine.font_height) * (i % 4)
            self.message_engine.draw(screen, self.COMMAND[i], (dx, dy))

        # draw cursor
        dx = self.text_rect[0] - 5
        dy = self.text_rect[1] + (self.LINE_HEIGHT+self.message_engine.font_height) * (self.command % 4)
        screen.blit(self.cursor, (dx, dy))

    def show(self):
        self.command = self.ATTACK
        self.is_visible = True


class BattleStatusWindow(Window):
    LINE_HEIGHT = 8

    def __init__(self, x, y, player, message_engine):
        # Window.__init__(self, rect)
        # self.text_rect = self.inner_rect.inflate(-32, -16)
        self.x = x
        self.y = y
        self.player = player
        self.message_engine = message_engine
        self.frame = 0
        self.health_percentage = self.player.current_health / self.player.health
        self.buffer = 4

    def draw(self, screen):
        pygame.draw.rect(screen, BLACK, Rect(self.x, self.y - self.buffer, BAR_SIZE * 2 + self.buffer, TILE_SIZE + (self.buffer * 5/2)))
        # pygame.draw.rect(screen, BLACK, Rect(self.x, self.y, TILE_SIZE * 2, TILE_SIZE))
        pygame.draw.rect(screen, Color(255, 45, 0, 0), Rect(self.x, self.y, BAR_SIZE * 2 * self.health_percentage, TILE_SIZE / 2))
        pygame.draw.rect(screen, Color(0, 135, 255, 0), Rect(self.x, self.y + (TILE_SIZE / 2) + (self.buffer / 2), BAR_SIZE * 2 * self.health_percentage, TILE_SIZE / 2))
        pygame.draw.circle(screen, BLACK, [self.x - 8, self.y + 16], 24)
        screen.blit(Character.images[self.player.name][0], (self.x - 24, self.y))
        health_status_info = str(self.player.current_health) + "/" + str(self.player.health)
        mana_status_info = str(self.player.current_mana) + "/" + str(self.player.mana)
        self.message_engine.draw_center(screen, health_status_info, Rect(self.x, self.y, BAR_SIZE * 2 * self.health_percentage, TILE_SIZE / 2))
        self.message_engine.draw_center(screen, mana_status_info, Rect(self.x, self.y + (TILE_SIZE / 2) + (self.buffer / 2), BAR_SIZE * 2 * self.health_percentage, TILE_SIZE / 2))
        # Window.draw(self, screen)
        if not self.is_visible:
            return
        status_info = [str(self.status[0]), "H"+str(self.status[1]), "M"+str(self.status[2])]
        for i in range(0, 3):
            dx = self.text_rect[0]
            dy = self.text_rect[1] + (self.LINE_HEIGHT+self.message_engine.font_height) * (i % 3)
            self.message_engine.draw(screen, status_info[i], (dx, dy))


class Class(Player):
    # Author: Junhong Wang
    # Date: 2016/11/10
    # Description: parameters for players

    def __init__(self, name, row, column, position, direction, is_leader, party,

                 health, mana, attack, intelligence, defence, magic_resistance, agility, critical_hit):
        Player.__init__(self, name, row, column, position, direction, is_leader, party)
        # parameters
        self.health = health
        self.current_health = health
        self.mana = mana
        self.current_mana = mana
        self.attack = attack
        self.intelligence = intelligence
        self.defence = defence
        self.magic_resistance = magic_resistance
        self.agility = agility
        self.critical_hit = critical_hit

        self.skills = []

        self.level = 1
        self.experience = 0
        self.status_points = 5
        self.skill_points = 0

        # equipments
        self.weapon = None
        self.head = None
        self.body = None
        self.arms = None
        self.legs = None
        self.boots = None
        self.accessory = None

class Knight(Class):
    # Author: Junhong Wang
    # Date: 2016/11/10
    # Description: parameters for Knight class
    def __init__(self, name, row, column, position, direction, is_leader, party):
        Class.__init__(self, name, row, column, position, direction, is_leader, party,
                       16, 1, 4, 0, 5, 3, 10, 8)
        self.skills.append(Skill("Deadly Sins", "Attack12",
                                 "A seven hit skill that consists of various slashes, "
                                 "several full circle spins and a backwards somersault.",
                                 0, 7))
        self.skills.append(Skill("Horizontal", "Attack1",
                                 "A simple sword skill slashing horizontally.",
                                 0, 2))
        self.skills.append(Skill("Horizontal Arc", "Attack1",
                                 "A flat two-part skill that involves a horizontal swing from left to right, "
                                 "followed by another horizontal swing in from right to left.",
                                 0, 3))
        self.skills.append(Skill("Horizontal Square", "Attack1",
                                 "A mid-level sword skill tracing the shape of a rhombus.",
                                 0, 4))



class Mage(Class):
    # Author: Junhong Wang
    # Date: 2016/11/10
    # Description: parameters for Mage class
    def __init__(self, name, row, column, position, direction, is_leader, party):
        Class.__init__(self, name, row, column, position, direction, is_leader, party,
                       16, 24, 0, 4, 4, 6, 4, 1)
        self.skills.append(Skill("Deadly Sins", "Attack1",
                                 "A seven hit skill that consists of various slashes, "
                                 "several full circle spins and a backwards somersault.",
                                 0, 7))
        self.skills.append(Skill("Horizontal", "Attack1",
                                 "A simple sword skill slashing horizontally.",
                                 0, 2))
        self.skills.append(Skill("Horizontal Arc", "Attack1",
                                 "A flat two-part skill that involves a horizontal swing from left to right, "
                                 "followed by another horizontal swing in from right to left.",
                                 0, 3))
        self.skills.append(Skill("Horizontal Square", "Attack1",
                                 "A mid-level sword skill tracing the shape of a rhombus.",
                                 0, 4))


class Tank(Class):
    # Author: Junhong Wang
    # Date: 2016/11/10
    # Description: parameters for Tank class
    def __init__(self, name, row, column, position, direction, is_leader, party):
        Class.__init__(self, name, row, column, position, direction, is_leader, party,
                       16, 1, 5, 0, 11, 1, 3, 1)
        self.skills.append(Skill("Deadly Sins", "Attack1",
                                 "A seven hit skill that consists of various slashes, "
                                 "several full circle spins and a backwards somersault.",
                                 0, 7))
        self.skills.append(Skill("Horizontal", "Attack1",
                                 "A simple sword skill slashing horizontally.",
                                 0, 2))
        self.skills.append(Skill("Horizontal Arc", "Attack1",
                                 "A flat two-part skill that involves a horizontal swing from left to right, "
                                 "followed by another horizontal swing in from right to left.",
                                 0, 3))
        self.skills.append(Skill("Horizontal Square", "Attack1",
                                 "A mid-level sword skill tracing the shape of a rhombus.",
                                 0, 4))


class Assassin(Class):
    # Author: Junhong Wang
    # Date: 2016/11/10
    # Description: parameters for Assassin class
    def __init__(self, name, row, column, position, direction, is_leader, party):
        Class.__init__(self, name, row, column, position, direction, is_leader, party,
                       16, 8, 4, 0, 4, 2, 12, 10)
        self.skills.append(Skill("Deadly Sins", "Attack1",
                                 "A seven hit skill that consists of various slashes, "
                                 "several full circle spins and a backwards somersault.",
                                 0, 7))
        self.skills.append(Skill("Horizontal", "Attack1",
                                 "A simple sword skill slashing horizontally.",
                                 0, 2
        self.skills.append(Skill("Horizontal Arc", "Attack1",
                                 "A flat two-part skill that involves a horizontal swing from left to right, "
                                 "followed by another horizontal swing in from right to left.",
                                 0, 3))
        self.skills.append(Skill("Horizontal Square", "Attack1",
                                 "A mid-level sword skill tracing the shape of a rhombus.",
                                 0, 4))


class Priest(Class):
    # Author: Junhong Wang
    # Date: 2016/11/10
    # Description: parameters for Priest class
    def __init__(self, name, row, column, position, direction, is_leader, party):
        Class.__init__(self, name, row, column, position, direction, is_leader, party,
                       16, 10, 0, 4, 3, 4, 4, 1)
        self.skills.append(Skill("Deadly Sins", "Attack1",
                                 "A seven hit skill that consists of various slashes, "
                                 "several full circle spins and a backwards somersault.",
                                 0, 7))
        self.skills.append(Skill("Horizontal", "Attack1",
                                 "A simple sword skill slashing horizontally.",
                                 0, 2))
        self.skills.append(Skill("Horizontal Arc", "Attack1",
                                 "A flat two-part skill that involves a horizontal swing from left to right, "
                                 "followed by another horizontal swing in from right to left.",
                                 0, 3))
        self.skills.append(Skill("Horizontal Square", "Attack1",
                                 "A mid-level sword skill tracing the shape of a rhombus.",
                                 0, 4))


class Enemy:
    # Author: Junhong Wang
    # Date: 2016/11/11
    # Description: parameters for enemy

    def __init__(self, id, name,
                 health, attack, intelligence, defence, magic_resistance, agility, critical_hit, experience):
        self.id = id
        self.name = name
        self.image = load_image("enemybatch", name+".png")
        self.health = health
        self.attack = attack
        self.intelligence = intelligence
        self.defence = defence
        self.magic_resistance = magic_resistance
        self.agility = agility
        self.critical_hit = critical_hit
        self.experience = experience
        self.level = 1

    def set_level(self, level):
        self.level = level
        self.health *= level
        self.attack *= level
        self.intelligence *= level
        self.defence *= level
        self.magic_resistance *= level
        self.agility *= level
        self.critical_hit *= level
        self.experience *= level


class PlayerStatusWindow(Window):


    # Author: Junhong Wang
    # Date: 2016/11/12
    # Description: status window when STATUS in command window is selected

    LINE_HEIGHT = 8
    STATUS = ["HP", "ATK", "INT", "DEF", "MGR", "AGL", "CRI", "EXE"]
    STATUS_DESCRIPTION = ["Increase the amount of health.",
                          "Increase the amount of attack damage",
                          "Increase the amount of spell power",
                          "Increase the amount of defence",
                          "Increase the amount of magic resistance",
                          "Increase the amount of agility",
                          "Increase the amount of critical hit rate",
                          "Experience points"]
    EQUIPMENTS = ["HEAD", "BODY", "ARMS", "LEGS", "BOOTS"]

    STATUS_WINDOW, SKILLS_WINDOW = 0, 1

    MAX_ALPHA = 200
    MIN_ALPHA = 100

    def __init__(self, rect, party, message_engine):
        Window.__init__(self, rect)
        self.top_rect = Rect(0, 0, self.rect.width, 0.1*self.rect.height)
        self.status_points_rect = Rect(0.05*rect.width, 0.1*rect.height, 0.35*rect.width, 0.6*rect.height)
        self.skill_points_rect = Rect(0.6*rect.width, 0.1*rect.height, 0.35*rect.width, 0.6*rect.height)
        self.level_rect = Rect(0.45*rect.width, 0.35*rect.height, 0.1*rect.width, 0.15*rect.height)
        self.experience_rect = Rect(0.45*rect.width, 0.55*rect.height, 0.1*rect.width, 0.15*rect.height)
        self.text_rect = Rect(0.05*rect.width, 0.75*rect.height, 0.9*rect.width, 0.2*rect.height)
        self.text_inner_rect = self.text_rect.inflate(-8, -8)

        self.page = 0
        self.party = party
        self.message_engine = message_engine
        self.background_image = load_image("data", "status_bg.png")
        self.cursor_left_image = load_image("data", "cursor_left.png")
        self.cursor_right_image = load_image("data", "cursor_right.png")
        self.status_cursor_image = load_image("data", "status_cursor.png")

        self.selected_player = self.party.members[self.page]
        self.status_before = []
        self.status_after = []
        self.status_images = []
        self.status_images.append(load_image("itemicon", "hp.png"))
        self.status_images.append(load_image("itemicon", "atk.png"))
        self.status_images.append(load_image("itemicon", "int.png"))
        self.status_images.append(load_image("itemicon", "def.png"))
        self.status_images.append(load_image("itemicon", "mgr.png"))
        self.status_images.append(load_image("itemicon", "agl.png"))
        self.status_images.append(load_image("itemicon", "cri.png"))
        self.status_images.append(load_image("itemicon", "exe.png"))

        self.frame = 0
        self.alpha = self.MIN_ALPHA
        self.alpha_flag = False
        self.alpha_speed = 3
        self.selection = self.STATUS_WINDOW

        self.status_cursor_position = 0

        self.points_distribution_flag = False

    def update(self):
        self.frame += 1

        if self.alpha > self.MAX_ALPHA:
            self.alpha_flag = False
        elif self.alpha < self.MIN_ALPHA:
            self.alpha_flag = True

        if self.alpha_flag:
            self.alpha += self.alpha_speed
        else:
            self.alpha -= self.alpha_speed

    def draw(self, screen):
        if not self.is_visible:
            return

        # prepare
        self.message_engine.set_color(BLACK)

        if not self.points_distribution_flag:
            selected_player = self.party.members[self.page]
            self.selected_player = selected_player
            hp = selected_player.health
            atk = selected_player.attack
            int = selected_player.intelligence
            de = selected_player.defence
            mgr = selected_player.magic_resistance
            agi = selected_player.agility
            cri = selected_player.critical_hit
            exe = selected_player.experience
            self.status_before = [selected_player.health, selected_player.attack, selected_player.intelligence,
                    selected_player.defence, selected_player.magic_resistance, selected_player.agility,
                    selected_player.critical_hit, selected_player.experience]
            self.status_after = [hp, atk, int, de, mgr, agi, cri, exe]

        self.selected_player.update()

        # background
        screen.blit(self.background_image, (0, 0))

        # top_rect
        offset_y = 8
        if not self.page == 0:
            screen.blit(self.cursor_left_image, (0.05*self.rect.width, offset_y))
        if not self.page == len(self.party.members) - 1:
            screen.blit(self.cursor_right_image, (0.95*self.rect.width-self.cursor_right_image.get_width(), offset_y))

        class_name = str(type(self.selected_player))[17:-2]
        self.message_engine.draw_center(screen, self.selected_player.name + " ( " + class_name + " )", self.top_rect)

        # status_window / skills_window
        trans_white_color = (WHITE[0], WHITE[1], WHITE[2], self.alpha)
        trans_orange_color = (ORANGE[0], ORANGE[1], ORANGE[2], self.alpha)
        if self.selection == self.STATUS_WINDOW:
            surface = pygame.Surface(self.status_points_rect.size, pygame.SRCALPHA)
            if self.points_distribution_flag:
                surface.fill((WHITE[0], WHITE[1], WHITE[2], self.MAX_ALPHA))

                # status_cursor
                dx = self.status_points_rect.left
                dy = self.status_points_rect.top + self.rect.height * 0.03 + (self.message_engine.font_height+self.LINE_HEIGHT) * (self.status_cursor_position+1)
                screen.blit(self.status_cursor_image, (dx, dy))

            else:
                surface.fill(trans_white_color)
            screen.blit(surface, self.status_points_rect.topleft)

            surface = pygame.Surface(self.skill_points_rect.size, pygame.SRCALPHA)
            surface.fill((WHITE[0], WHITE[1], WHITE[2], self.MIN_ALPHA))
            screen.blit(surface, self.skill_points_rect.topleft)

        elif self.selection == self.SKILLS_WINDOW:
            surface = pygame.Surface(self.skill_points_rect.size, pygame.SRCALPHA)
            if self.points_distribution_flag:
                surface.fill((WHITE[0], WHITE[1], WHITE[2], self.MAX_ALPHA))

                # status_cursor
                dx = self.skill_points_rect.left
                dy = self.skill_points_rect.top + self.rect.height * 0.03 + (
                                                                             self.message_engine.font_height + self.LINE_HEIGHT) * (
                                                                             self.status_cursor_position + 1)
                screen.blit(self.status_cursor_image, (dx, dy))

            else:
                surface.fill(trans_white_color)
            screen.blit(surface, self.skill_points_rect.topleft)

            surface = pygame.Surface(self.status_points_rect.size, pygame.SRCALPHA)
            surface.fill((WHITE[0], WHITE[1], WHITE[2], self.MIN_ALPHA))
            screen.blit(surface, self.status_points_rect.topleft)

        # level_rect
        surface = pygame.Surface(self.level_rect.size, pygame.SRCALPHA)
        surface.fill(trans_orange_color)
        screen.blit(surface, self.level_rect.topleft)
        # experience_rect
        surface = pygame.Surface(self.experience_rect.size, pygame.SRCALPHA)
        surface.fill(trans_orange_color)
        screen.blit(surface, self.experience_rect.topleft)

        # text_rect
        pygame.draw.rect(screen, WHITE, self.text_rect, 0)
        pygame.draw.rect(screen, BLACK, self.text_inner_rect, 0)

        # text on status_window
        dx = self.status_points_rect.left
        dy = self.status_points_rect.top
        self.message_engine.draw(screen, " STATUS"+"       "+str(self.selected_player.status_points)+"pt", (dx, dy))

        offset_y = self.rect.height * 0.03
        offset_x = self.status_points_rect.width * 0.5
        cursor_offset = offset_x * 0.5
        for i in range(0, len(self.STATUS)):
            dx = self.status_points_rect.left
            dy = self.status_points_rect.top + offset_y + (self.message_engine.font_height+self.LINE_HEIGHT) * (i+1)
            screen.blit(self.status_images[i], (dx, dy))
            self.message_engine.draw(screen, self.STATUS[i], (dx+self.status_images[i].get_rect().width, dy))
            if self.points_distribution_flag and self.selected_player.status_points:
                if i == self.status_cursor_position:
                    screen.blit(self.cursor_right_image, (dx+self.status_images[i].get_rect().width+offset_x+cursor_offset, dy))
            if self.status_after[i] != self.status_before[i]:
                if i == self.status_cursor_position:
                    screen.blit(self.cursor_left_image,
                                (dx + self.status_images[i].get_rect().width + offset_x - cursor_offset, dy))
                self.message_engine.set_color(RED)
                self.message_engine.draw(screen, str(self.status_after[i]),
                                         (dx+self.status_images[i].get_rect().width+offset_x, dy))
                self.message_engine.set_color(BLACK)
            else:
                self.message_engine.draw(screen, str(self.status_after[i]),
                                         (dx + self.status_images[i].get_rect().width + offset_x, dy))

        screen.blit(self.selected_player.image, (0.45*self.rect.width+0.5*TILE_SIZE, 0.15*self.rect.height+0.5*TILE_SIZE))

        # text on level_rect
        dx = self.level_rect.left
        dy = self.level_rect.top
        self.message_engine.draw(screen, "LEVEL", (dx, dy))
        dx = self.level_rect.centerx - self.message_engine.font_width*0.5
        dy = self.level_rect.centery
        self.message_engine.draw(screen, str(self.selected_player.level), (dx, dy))

        # text on experience_rect
        dx = self.experience_rect.left
        dy = self.experience_rect.top
        self.message_engine.draw(screen, "EXP", (dx+self.message_engine.font_width, dy))
        self.message_engine.draw(screen, "NEXT",
                                 (dx+0.5*self.message_engine.font_width, dy+self.message_engine.font_height))
        dx = self.experience_rect.centerx
        self.message_engine.draw(screen, str(self.selected_player.experience),
                                 (dx-self.message_engine.font_width*0.5, dy+self.message_engine.font_height*2))

        # text on skills_window
        dx = self.skill_points_rect.left
        dy = self.skill_points_rect.top
        offset_y = self.rect.height * 0.03
        offset_x = self.rect.width * 0.25
        self.message_engine.draw(screen, " SKILLS"+"       "+str(self.selected_player.skill_points)+"pt", (dx, dy))
        for i in range(0, 4):
            name = self.selected_player.skills[i].name
            name_list = name.split()
            name_shortened = ""
            for word in name_list:
                name_shortened += word[:1]
            self.message_engine.draw(screen, " "+name_shortened,
                                     (dx, dy+offset_y+(self.message_engine.font_height+self.LINE_HEIGHT)*(i+1)))
            self.message_engine.draw(screen, str(self.selected_player.skills[i].level), (dx+offset_x, dy+offset_y+(self.message_engine.font_height+self.LINE_HEIGHT)*(i+1)))

        # text on text_rect
        dx = self.text_inner_rect.left
        dy = self.text_inner_rect.top
        self.message_engine.set_color(WHITE)
        if self.points_distribution_flag:
            if self.selection == self.STATUS_WINDOW:
                description = self.STATUS_DESCRIPTION[self.status_cursor_position]
                self.message_engine.draw(screen, description, (dx, dy))
            if self.selection == self.SKILLS_WINDOW:
                selected_skill = self.party.members[self.page].skills[self.status_cursor_position]
                name = selected_skill.name
                description = selected_skill.description
                self.message_engine.draw(screen, name, (dx, dy))
                self.message_engine.draw(screen, description, (dx, dy+self.message_engine.font_height+self.LINE_HEIGHT))

        # finish drawing
        # self.message_engine.set_color(WHITE)

    def play_bgm(self):
        bgm_file_name = "shop.ogg"
        bgm_file_path = os.path.join("bgm", bgm_file_name)
        pygame.mixer.music.load(bgm_file_path)
        pygame.mixer.music.play(-1)


class Skill:


    MAX_LIFE = 10

    def __init__(self, name, image_name, description, bonus_power, bonus_rate):
        self.name = name
        self.image_name = image_name
        self.description = description
        # addition to player power
        self.bonus_power = bonus_power
        # multiplication with player power
        self.bonus_rate = bonus_rate

        self.level = 0
        self.images = split_image(load_image("skilleffect", image_name+".png"), SKILL_EFFECT_SIZE)

        self.life = 0

    def draw(self, screen):
        index = (len(self.images) - 1) - int(self.life / (self.MAX_LIFE / len(self.images)))
        if index < 0:
            index = 0
        # print(index)
        center_rect = self.images[index].get_rect(center=SCREEN_RECT.center)
        blend_factor = self.life % (self.MAX_LIFE / len(self.images))
        print(blend_factor)
        if index + 1 < len(self.images):
            image = blend_image(self.images[index], self.images[index+1], blend_factor)
        else:
            image = self.images[index]
        screen.blit(image, center_rect)
        self.life -= 1


    def invoke(self):
        self.life = self.MAX_LIFE
        sounds["sword_slice"].play()



class Shop:

    items = []

    def __init__(self, name):
        self.name = name
        self.items_on_sale = []
        self.load()

    def load(self):
        file_path = os.path.join("data", self.name+".shop")
        file = open(file_path)
        for line in file:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            data = line.split(",")
            for id in data:
                self.items_on_sale.append(Shop.items[int(id)])
        file.close()


class Clerk(Character):

    def __init__(self, name, row, column, position, direction, move_type, message, shop):
        Character.__init__(self, name, row, column, position, direction, move_type, message)
        self.shop = shop


class ShopWindow(Window):
    # Author: Junhong Wang
    # Date: 2016/11/19
    # Description: Player can buy item at a shop when talking with a clerk

    def __init__(self, rect, message_engine):
        Window.__init__(self, rect)
        self.clerk = None
        self.message_engine = message_engine
        self.inventory_image = load_image("data", "inventory.png")
        self.shop_shelf_image = load_image("data", "shopshelf.png")

        self.shop_shelf_rect = Rect(SCREEN_RECT.width*0.6, SCREEN_RECT.height*0.15,
                                    self.shop_shelf_image.get_rect().width, self.shop_shelf_image.get_rect().height)
        self.inventory_rect = Rect(SCREEN_RECT.width*0.1, SCREEN_RECT.height*0.1,
                                   self.inventory_image.get_rect().width, self.inventory_image.get_rect().height)

        self.shop_background_image = load_image("data", "shop_background.png")
        self.text_rect = Rect(0.05 * rect.width, 0.75 * rect.height, 0.9 * rect.width, 0.2 * rect.height)
        self.text_inner_rect = self.text_rect.inflate(-8, -8)
        self.cursor_image = load_image("data", "hand_cursor.png")
        self.cursor_grab_image = load_image("data", "hand_cursor_grab.png")
        self.cursor_position = 0
        self.cursor_in_shop_shelf = False
        self.items_on_sale = None
        self.is_grabbing = False
        self.is_grabbing_product = False

        self.selected_item = None
        self.selected_item_position = None

        self.gold_rect = Rect(0, 0, 100, self.message_engine.font_height+8)
        self.gold_inner_rect = self.gold_rect.inflate(-8, -8)

        self.purchase_price = 0
        self.gold_decrease_speed = 7

        self.price_rect = Rect(0, 0, 100, self.message_engine.font_height+8)
        self.price_inner_rect = self.price_rect.inflate(-8, -8)

    def set_clerk(self, clerk):
        self.clerk = clerk
        self.items_on_sale = self.clerk.shop.items_on_sale
        self.show()

    def update(self):
        if self.cursor_in_shop_shelf:
            if self.cursor_position == 10:
                self.cursor_position = 7
            elif self.cursor_position == 11:
                self.cursor_position = 8

    def draw(self, screen):
        # draw boards
        screen.blit(self.shop_background_image, (0, 0))
        screen.blit(self.inventory_image, self.inventory_rect.topleft)
        screen.blit(self.shop_shelf_image, self.shop_shelf_rect.topleft)

        # draw items (inventory)
        offset = 15
        for i in range(len(Player.inventory)):
            if Player.inventory[i]:
                dx = self.inventory_rect.left + 50*(i % 5)
                dy = self.inventory_rect.top + 50*int(i / 5)
                screen.blit(Player.inventory[i].image, (dx+offset, dy+offset))
        # draw items (shop)
        dx = self.shop_shelf_rect.left
        dy = self.shop_shelf_rect.top
        offset1_x = 25
        offset1_y = 25
        offset2_x = 50
        offset2_y = 50
        for i in range(len(self.items_on_sale)):
            screen.blit(self.items_on_sale[i].image, (dx+offset1_x+offset2_x*(i % 3), dy+offset1_y+offset2_y*int(i / 3)))

        # draw the hand cursor
        offset1 = 50
        offset3 = 15  # so that the finger will point to the center of the square
        if not self.cursor_in_shop_shelf:
            offset1_factor_x = self.cursor_position % 5
            offset1_factor_y = int(self.cursor_position / 5)
            offset2 = 10

            if not self.is_grabbing:
                screen.blit(self.cursor_image,
                            (self.inventory_rect.left+offset1*offset1_factor_x+offset2,
                                self.inventory_rect.top+offset1*offset1_factor_y+offset2+offset3))
            else:
                screen.blit(self.selected_item.image, (self.inventory_rect.left + offset1 * offset1_factor_x + offset2,
                                                 self.inventory_rect.top + offset1 * offset1_factor_y + offset2 + offset3))
                screen.blit(self.cursor_grab_image,
                            (self.inventory_rect.left + offset1 * offset1_factor_x + offset2,
                             self.inventory_rect.top + offset1 * offset1_factor_y + offset2 + offset3))
        else:
            # if the hand cursor is in the shop shelf
            offset1_factor_x = self.cursor_position % 3
            offset1_factor_y = int(self.cursor_position / 3)
            offset2 = 20
            if not self.is_grabbing:
                screen.blit(self.cursor_image,
                            (self.shop_shelf_rect.left + offset1 * offset1_factor_x + offset2,
                             self.shop_shelf_rect.top + offset1 * offset1_factor_y + offset2 + offset3))
            else:
                screen.blit(self.selected_item.image, (self.shop_shelf_rect.left + offset1 * offset1_factor_x + offset2,
                                                 self.shop_shelf_rect.top + offset1 * offset1_factor_y + offset2 + offset3))
                screen.blit(self.cursor_grab_image,
                            (self.shop_shelf_rect.left + offset1 * offset1_factor_x + offset2,
                             self.shop_shelf_rect.top + offset1 * offset1_factor_y + offset2 + offset3))

        if self.cursor_in_shop_shelf:
            if self.cursor_position < len(self.items_on_sale):
                if not self.is_grabbing_product:
                    # draw price box
                    dx = self.shop_shelf_rect.left
                    dy = self.shop_shelf_rect.top
                    offset1 = 50
                    offset1 = 50
                    offset1_factor_x = self.cursor_position % 3
                    offset1_factor_y = int(self.cursor_position / 3)
                    offset2 = 20

                    self.price_rect.topleft = (dx + offset1 * offset1_factor_x + offset2, dy + offset1 * offset1_factor_y)
                    self.price_inner_rect = self.price_rect.inflate(-8, -8)
                    pygame.draw.rect(screen, WHITE, self.price_rect, 0)
                    pygame.draw.rect(screen, BLACK, self.price_inner_rect, 0)

                    # draw price
                    dx = self.price_inner_rect.left
                    dy = self.price_inner_rect.top
                    self.message_engine.draw(screen, str(self.items_on_sale[self.cursor_position].price), (dx, dy))
                    dx = self.price_inner_rect.right - self.message_engine.font_width
                    self.message_engine.draw(screen, "G", (dx, dy))


        # draw the text boxes
        pygame.draw.rect(screen, WHITE, self.text_rect, 0)
        pygame.draw.rect(screen, BLACK, self.text_inner_rect, 0)

        # draw the texts
        if self.cursor_in_shop_shelf:
            if self.cursor_position < len(self.items_on_sale):
                dx = self.text_inner_rect.left
                dy = self.text_inner_rect.top
                self.message_engine.draw(screen,
                                         self.items_on_sale[self.cursor_position].description + ", "
                                         + str(self.items_on_sale[self.cursor_position].price) + "G",
                                         (dx, dy))
        else:
            # if the cursor is in the inventory
            try:
                if Player.inventory[self.cursor_position]:
                    dx = self.text_inner_rect.left
                    dy = self.text_inner_rect.top
                    self.message_engine.draw(screen,
                                             Player.inventory[self.cursor_position].description + ", "
                                             + str(Player.inventory[self.cursor_position].price) + "G",
                                             (dx, dy))
            except IndexError:
                pass

        # draw gold box
        pygame.draw.rect(screen, WHITE, self.gold_rect, 0)
        pygame.draw.rect(screen, BLACK, self.gold_inner_rect, 0)

        # draw the amount of gold
        dx = self.gold_inner_rect.left
        dy = self.gold_inner_rect.top

        if self.purchase_price == 0:
            pass
        elif self.purchase_price - self.gold_decrease_speed >= 0:
            self.purchase_price -= self.gold_decrease_speed
            Player.gold -= self.gold_decrease_speed
        else:
            # self.purchase_price - self.gold_decrease_speed < 0
            Player.gold -= self.purchase_price
            self.purchase_price = 0

        self.message_engine.draw(screen, str(Player.gold), (dx, dy))

        dx = self.gold_inner_rect.right - self.message_engine.font_width
        self.message_engine.draw(screen, "G", (dx, dy))

    def play_bgm(self):
        bgm_file_name = "shop.ogg"
        bgm_file_path = os.path.join("bgm", bgm_file_name)
        pygame.mixer.music.load(bgm_file_path)
        pygame.mixer.music.play(-1)


class ItemWindow(Window):

    # Author: Junhong Wang
    # Date: 11/23/2016
    # Description: window for the items and player equipments

    STATUS = ["HP", "ATK", "INT", "DEF", "MGR", "AGL", "CRI", "EXE"]
    INVENTORY_RECT, EQUIPMENT_RECT, BAG_RECT, DROP_RECT = 0, 1, 2, 3

    def __init__(self, rect, message_engine, party):
        Window.__init__(self, rect)
        self.message_engine = message_engine
        self.background_image = load_image("data", "item_window_bg.png")
        self.inventory_image = load_image("data", "inventory.png")
        self.bag_image = load_image("data", "bag.png")
        self.hand_cursor_image = load_image("data", "hand_cursor.png")
        self.hand_cursor_grab_image = load_image("data", "hand_cursor_grab.png")
        self.drop_image = load_image("data", "drop.png")
        self.weapon_equipment_image = load_image("data", "weapon.png")
        self.body_equipment_image = load_image("data", "body.png")
        self.head_equipment_image = load_image("data", "head.png")
        self.hand_equipment_image = load_image("data", "hand.png")
        self.boots_equipment_image = load_image("data", "boots.png")
        self.accessory_equipment_image = load_image("data", "accessory.png")
        self.player_info_rect = Rect(0, 0, SCREEN_RECT.width, SCREEN_RECT.height*0.1)
        self.bag_rect = Rect(0, SCREEN_RECT.height*0.1, SCREEN_RECT.width*0.45, SCREEN_RECT.height*0.1)
        self.inventory_rect = Rect(SCREEN_RECT.width*0.45, SCREEN_RECT.height*0.1,
                                   SCREEN_RECT.width*0.55, SCREEN_RECT.height*0.6)
        self.equipment_rect = Rect(0, SCREEN_RECT.height*0.2, SCREEN_RECT.width*0.45, SCREEN_RECT.height*0.5)
        self.status_rect = Rect(0, SCREEN_RECT.height*0.7, SCREEN_RECT.width, SCREEN_RECT.height*0.3)
        self.text_rect = Rect(0, SCREEN_RECT.height*0.9, SCREEN_RECT.width, SCREEN_RECT.height*0.1)
        self.text_inner_rect = self.text_rect.inflate(-8, -8)
        self.party = party

        self.status_images = []
        self.status_images.append(load_image("itemicon", "hp.png"))
        self.status_images.append(load_image("itemicon", "atk.png"))
        self.status_images.append(load_image("itemicon", "int.png"))
        self.status_images.append(load_image("itemicon", "def.png"))
        self.status_images.append(load_image("itemicon", "mgr.png"))
        self.status_images.append(load_image("itemicon", "agl.png"))
        self.status_images.append(load_image("itemicon", "cri.png"))
        self.status_images.append(load_image("itemicon", "exe.png"))

        self.cursor_right_image = load_image("data", "cursor_right.png")
        self.cursor_left_image = load_image("data", "cursor_left.png")

        self.cursor_is_in = self.INVENTORY_RECT
        self.cursor_position = 0
        self.is_grabbing = False
        self.selected_item = None
        self.selected_item_position = None
        self.selected_item_from = None

        self.page = 0
        self.selected_player = self.party.members[self.page]


    def update(self):
        self.party.members[0].update()

    def draw(self, screen):
        screen.blit(self.background_image, (0, 0))

        # draw selected player info
        dx = self.player_info_rect.left
        dy = self.player_info_rect.top
        offset_y = 10
        screen.blit(self.cursor_left_image, (dx, dy + offset_y))
        dx = self.player_info_rect.right
        screen.blit(self.cursor_right_image, (dx - self.cursor_right_image.get_rect().width, dy + offset_y))
        self.message_engine.draw_center(screen, self.selected_player.name, self.player_info_rect)

        # bag rect
        dx = self.bag_rect.centerx
        dy = self.bag_rect.top
        offset_x = self.bag_image.get_rect().width*0.5
        screen.blit(self.bag_image, (dx - offset_x, dy))

        # draw items in bag
        for i in range(5):
            item = self.selected_player.bag[i]
            if item:
                offset2_x = 25 - item.image.get_rect().width*0.5
                offset3_x = 50 * i
                offset2_y = self.bag_image.get_rect().height * 0.5 - item.image.get_rect().height * 0.5
                screen.blit(item.image, (dx - offset_x + offset2_x + offset3_x, dy + offset2_y))


        # inventory rect
        dx = self.inventory_rect.left
        dy = self.inventory_rect.top
        offset_x = 10
        offset_y = 20
        screen.blit(self.inventory_image, (dx + offset_x, dy + offset_y))
        offset_x = self.inventory_image.get_rect().width + 20
        offset_y = self.inventory_image.get_rect().height - 30
        screen.blit(self.drop_image, (dx + offset_x, dy + offset_y))

        # draw items in the inventory
        for i in range(len(Player.inventory)):
            if Player.inventory[i]:
                dx = self.inventory_rect.left
                dy = self.inventory_rect.top
                offset_x = 10
                offset_y = 20
                offset2_x = 25 - Player.inventory[i].image.get_rect().width*0.5
                offset2_y = 25 - Player.inventory[i].image.get_rect().height*0.5
                offset3_x = 50 * (i % 5)
                offset3_y = 50 * int(i / 5)
                screen.blit(Player.inventory[i].image,
                            (dx + offset_x + offset2_x + offset3_x, dy + offset_y + offset2_y + offset3_y))

        # equipment rect
        dx = self.equipment_rect.left
        dy = self.equipment_rect.top
        offset_x = 20
        offset_y = 20
        screen.blit(self.weapon_equipment_image, (dx + offset_x, dy + offset_y))
        offset_y += 20 + 50
        screen.blit(self.accessory_equipment_image, (dx + offset_x, dy + offset_y))
        offset_y += 20 + 50
        screen.blit(self.boots_equipment_image, (dx + offset_x, dy + offset_y))
        dx = self.equipment_rect.centerx
        dy = self.equipment_rect.centery
        offset_x = self.party.members[0].image.get_rect().width*0.5
        offset_y = self.party.members[0].image.get_rect().height*0.5
        screen.blit(self.party.members[0].image,
                    (dx - offset_x, dy - offset_y))
        dx = self.equipment_rect.right
        dy = self.equipment_rect.top
        offset_x = 20 + 50
        offset_y = 20
        screen.blit(self.head_equipment_image, (dx - offset_x, dy + offset_y))
        offset_y += 20 + 50
        screen.blit(self.body_equipment_image, (dx - offset_x, dy + offset_y))
        offset_y += 20 + 50
        screen.blit(self.hand_equipment_image, (dx - offset_x, dy + offset_y))

        # draw items in equipment rect
        equipments = [self.selected_player.weapon, self.selected_player.head,
                      self.selected_player.accessory, self.selected_player.body,
                      self.selected_player.boots, self.selected_player.arms]
        for i in range(len(equipments)):
            if equipments[i]:
                if i % 2 == 0:
                    dx = self.equipment_rect.left
                    dy = self.equipment_rect.top
                    offset_x = 20
                    offset_y = 20
                    offset2_x = 25 - equipments[i].image.get_rect().width*0.5
                    offset2_y = 25 - equipments[i].image.get_rect().height*0.5
                    offset3_y = int(i / 2) * (20 + 50)
                    screen.blit(equipments[i].image,
                                (dx + offset_x + offset2_x, dy + offset_y + offset2_y + offset3_y))
                else:
                    dx = self.equipment_rect.right
                    dy = self.equipment_rect.top
                    offset_x = 20 + 25
                    offset_y = 20
                    offset2_x = 25 - equipments[i].image.get_rect().width * 0.5
                    offset2_y = 25 - equipments[i].image.get_rect().height * 0.5
                    offset3_y = int(i / 2) * (20 + 50)
                    screen.blit(equipments[i].image,
                                (dx - offset_x - offset2_x, dy + offset_y + offset2_y + offset3_y))

        # status rect
        status = [self.selected_player.health, self.selected_player.attack, self.selected_player.intelligence,
                  self.selected_player.defence, self.selected_player.magic_resistance, self.selected_player.agility,
                  self.selected_player.critical_hit, self.selected_player.experience]
        for i in range(len(self.STATUS)):
            dx = self.status_rect.left
            dy = self.status_rect.top
            dx += self.status_rect.width * 0.33 * int(i / 3)
            dy += 30 * (i % 3)
            screen.blit(self.status_images[i], (dx, dy))
            self.message_engine.draw(screen, self.STATUS[i], (dx + 30, dy))
            screen.blit(self.cursor_right_image, (dx + 70, dy))
            self.message_engine.draw(screen, str(status[i]), (dx + 100, dy))

        # text rect
        pygame.draw.rect(screen, WHITE, self.text_rect, 0)
        pygame.draw.rect(screen, BLACK, self.text_inner_rect, 0)

        # draw cursor
        if self.cursor_is_in == self.INVENTORY_RECT:
            dx = self.inventory_rect.left
            dy = self.inventory_rect.top
            offset_x = 10 + 25 - self.hand_cursor_image.get_rect().width*0.5
            offset_y = 20 + 25 - self.hand_cursor_image.get_rect().height*0.5
            offset2_x = 50 * (self.cursor_position % 5)
            offset2_y = 50 * int(self.cursor_position / 5)

            # draw selected item if exists
            if self.selected_item:
                screen.blit(self.selected_item.image, (dx + offset_x + offset2_x, dy + offset_y + offset2_y))

            if self.is_grabbing:
                screen.blit(self.hand_cursor_grab_image, (dx + offset_x + offset2_x, dy + offset_y + offset2_y))
            else:
                screen.blit(self.hand_cursor_image, (dx + offset_x + offset2_x, dy + offset_y + offset2_y))
        elif self.cursor_is_in == self.DROP_RECT:
            dx = self.inventory_rect.left
            dy = self.inventory_rect.top
            offset_x = self.inventory_image.get_rect().width + 20
            offset_y = self.inventory_image.get_rect().height - 30
            offset2_x = self.drop_image.get_rect().width*0.5 - self.hand_cursor_image.get_rect().width*0.5
            offset2_y = self.drop_image.get_rect().height*0.5 - self.hand_cursor_image.get_rect().height*0.5

            # draw selected item if exists
            if self.selected_item:
                screen.blit(self.selected_item.image, (dx + offset_x + offset2_x, dy + offset_y + offset2_y))

            if self.is_grabbing:
                screen.blit(self.hand_cursor_grab_image, (dx + offset_x + offset2_x, dy + offset_y + offset2_y))
            else:
                screen.blit(self.hand_cursor_image, (dx + offset_x + offset2_x, dy + offset_y + offset2_y))
        elif self.cursor_is_in == self.BAG_RECT:
            dx = self.bag_rect.centerx
            dy = self.bag_rect.top
            offset_x = self.bag_image.get_rect().width * 0.5
            offset2_x = 25 - self.hand_cursor_image.get_rect().width*0.5
            offset2_y = 25 - self.hand_cursor_image.get_rect().height*0.5
            offset3_x = 50 * self.cursor_position

            # draw selected item if exists
            if self.selected_item:
                screen.blit(self.selected_item.image, (dx - offset_x + offset2_x + offset3_x, dy + offset2_y))

            if self.is_grabbing:
                screen.blit(self.hand_cursor_grab_image, (dx - offset_x + offset2_x + offset3_x, dy + offset2_y))
            else:
                screen.blit(self.hand_cursor_image, (dx - offset_x + offset2_x + offset3_x, dy + offset2_y))
        elif self.cursor_is_in == self.EQUIPMENT_RECT:
            if self.cursor_position % 2 == 0:
                dx = self.equipment_rect.left
                dy = self.equipment_rect.top
                offset_x = 20
                offset_y = 20
                offset2_x = self.weapon_equipment_image.get_rect().width*0.5 - self.hand_cursor_image.get_rect().width*0.5
                offset2_y = self.weapon_equipment_image.get_rect().height*0.5 - self.hand_cursor_image.get_rect().height*0.5
            else:
                dx = self.equipment_rect.right
                dy = self.equipment_rect.top
                offset_x = - 20 - 50
                offset_y = 20
                offset2_x = self.weapon_equipment_image.get_rect().width * 0.5 - self.hand_cursor_image.get_rect().width * 0.5
                offset2_y = self.weapon_equipment_image.get_rect().height * 0.5 - self.hand_cursor_image.get_rect().height * 0.5

            offset3_y = 20 + 50

            # draw selected item if exists
            if self.selected_item:
                screen.blit(self.selected_item.image, (dx + offset_x + offset2_x,
                             dy + offset_y + offset2_y + offset3_y * int(self.cursor_position / 2)))

            if self.is_grabbing:
                screen.blit(self.hand_cursor_grab_image,
                            (dx + offset_x + offset2_x,
                             dy + offset_y + offset2_y + offset3_y * int(self.cursor_position / 2)))
            else:
                screen.blit(self.hand_cursor_image,
                            (dx + offset_x + offset2_x,
                             dy + offset_y + offset2_y + offset3_y * int(self.cursor_position / 2)))


if __name__ == "__main__":
    pyRPG()

