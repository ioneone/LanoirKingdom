import os
import pygame


def add_rows_and_columns_to_character_chip_dat(directory, file_name):
    file_path = os.path.join(directory, file_name)
    with open(file_path, 'r') as input_file, open('charachip.dat', 'w') as output_file:
        for line in input_file:
            line = line.rstrip()
            line += ",4,4"
            print(line)
            output_file.write(line+"\n")


def get_list_directory(directory):
    return os.listdir(directory)


def create_enemy_batch_dat():
    list = get_list_directory("enemybatch")
    file = open("enemybatch.dat", 'w')
    for i in range(1, len(list)):
        file.write(list[i][:-4]+"\n")


create_enemy_batch_dat()
# add_rows_and_columns_to_character_chip_dat("data", "charachip.dat")

# Be aware that MP3 support is limited.
# On some systems an unsupported format can crash the program,
# e.g. Debian Linux. Consider using OGG instead.
# pygame.init()
# pygame.mixer.music.load("bgm/test2.ogg")
# pygame.mixer.music.play(-1)