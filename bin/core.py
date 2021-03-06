# OpenAssistant 0.03
# 2016 General Public License V3
# By Andrew Vavrek, Clayton G. Hobbs, Jezra, Jonathan Kulp

# core.py - System Core

import sys
import signal
import os.path
import subprocess
from gi.repository import GObject, GLib

from bin.recognizer import Recognizer
from bin.utilities import *
from bin.numbers import NumberParser

class Assistant:

    def __init__(self):
        self.ui = None
        self.options = {}
        self.continuous_listen = False

        # Load Configuration
        self.config = Config()
        self.options = vars(self.config.options)
        self.commands = self.options['commands']

        # Create Number Parser
        self.number_parser = NumberParser()

        # Create Hasher
        self.hasher = Hasher(self.config)

        # Create Strings File
        self.update_voice_commands_if_changed()

        if self.options['interface']:
            if self.options['interface'] == "g":
                from bin.gui import GTKInterface as UI
            elif self.options['interface'] == "gt":
                from bin.gui import GTKTrayInterface as UI
            else:
                print("no GUI defined")
                sys.exit()

            self.ui = UI(self.options, self.options['continuous'])
            self.ui.connect("command", self.process_command)
            # Able To Load Icon?
            icon = self.load_resource("icon_small.png")
            if icon:
                self.ui.set_icon_active_asset(icon)
            # Able To Load Inactive Icon?
            icon_inactive = self.load_resource("icon_inactive_small.png")
            if icon_inactive:
                self.ui.set_icon_inactive_asset(icon_inactive)

        if self.options['history']:
            self.history = []

        # Update Language If Changed
        self.language_updater = LanguageUpdater(self.config)
        self.language_updater.update_language_if_changed()

        # Create Recognizer
        self.recognizer = Recognizer(self.config)
        self.recognizer.connect('finished', self.recognizer_finished)

    def update_voice_commands_if_changed(self):
        """USE HASHES TO TEST IF THE VOICE COMMANDS HAVE CHANGED"""
        stored_hash = self.hasher['voice_commands']

        # Calculate The Hash The Voice Commands Have Right Now
        hasher = self.hasher.get_hash_object()
        for voice_cmd in self.commands.keys():
            hasher.update(voice_cmd.encode('utf-8'))
            # Add A Separator To Avoid Odd BehaviorA
            hasher.update('\n'.encode('utf-8'))
        new_hash = hasher.hexdigest()

        if new_hash != stored_hash:
            self.create_strings_file()
            self.hasher['voice_commands'] = new_hash
            self.hasher.store()

    def create_strings_file(self):
        # Open Strings File
        with open(self.config.strings_file, 'w') as strings:
            # Add Command Words To The Corpus
            for voice_cmd in sorted(self.commands.keys()):
                strings.write(voice_cmd.strip().replace('%d', '') + "\n")
            # Add Number Words To The Corpus
            for word in self.number_parser.number_words:
                strings.write(word + " ")
            strings.write("\n")

    def log_history(self, text):
        if self.options['history']:
            self.history.append(text)
            if len(self.history) > self.options['history']:
                # Pop Off First Item
                self.history.pop(0)

            # Open And Truncate History File
            with open(self.config.history_file, 'w') as hfile:
                for line in self.history:
                    hfile.write(line + '\n')

    def run_command(self, cmd):
        """PRINT COMMAND AND RUN"""
        print("\x1b[32m< ! >\x1b[0m", cmd)
        self.recognizer.pause()
        subprocess.call(cmd, shell=True)
        self.recognizer.listen()

    def recognizer_finished(self, recognizer, text):
        t = text.lower()
        numt, nums = self.number_parser.parse_all_numbers(t)
        # Is There A Matching Command?
        if t in self.commands:
            # Run The 'valid_sentence_command' If It's Set
            os.system('clear')
            print("OpenAssistant: \x1b[32mListening\x1b[0m")
            if self.options['valid_sentence_command']:
                subprocess.call(self.options['valid_sentence_command'],
                                shell=True)
            cmd = self.commands[t]
            # Should We Be Passing Words?
            os.system('clear')
            print("OpenAssistant: \x1b[32mListening\x1b[0m")
            if self.options['pass_words']:
                cmd += " " + t
            print("\x1b[32m< ! >\x1b[0m {0}".format(t))
            self.run_command(cmd)
            self.log_history(text)
        elif numt in self.commands:
            # Run 'valid_sentence_command' Set
            os.system('clear')
            print("OpenAssistant: \x1b[32mListening\x1b[0m")
            if self.options['valid_sentence_command']:
                subprocess.call(self.options['valid_sentence_command'],
                                shell=True)
            cmd = self.commands[numt]
            cmd = cmd.format(*nums)
            # Should We Be Passing Words?
            if self.options['pass_words']:
                cmd += " " + t
            print("\x1b[32m< ! >\x1b[0m {0}".format(t))
            self.run_command(cmd)
            self.log_history(text)
        else:
            # Run The Invalid_sentence_command If It's Set
            if self.options['invalid_sentence_command']:
                subprocess.call(self.options['invalid_sentence_command'],
                                shell=True)
            print("\x1b[31m< ? >\x1b[0m {0}".format(t))
        # If There Is A Ui And We Are Not In Continuous Listen
        if self.ui:
            if not self.continuous_listen:
                # Stop Listening
                self.recognizer.pause()
            # Tell Ui To Finish
            self.ui.finished(t)

    def run(self):
        if self.ui:
            self.ui.run()
        else:
            self.recognizer.listen()

    def quit(self):
        sys.exit()

    def process_command(self, UI, command):
        print(command)
        if command == "listen":
            self.recognizer.listen()
        elif command == "stop":
            self.recognizer.pause()
        elif command == "continuous_listen":
            self.continuous_listen = True
            self.recognizer.listen()
        elif command == "continuous_stop":
            self.continuous_listen = False
            self.recognizer.pause()
        elif command == "quit":
            self.quit()


def run():
    # Create Core Object
    core = Assistant()
    # Initialize Gobject Threads
    GObject.threads_init()
    # Create Main Loop
    main_loop = GObject.MainLoop()
    # Handle Signal Interrupts
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # Run Core
    core.run()
    # Start Main Loop
    try:
        main_loop.run()
    except:
        main_loop.quit()
        sys.exit()
