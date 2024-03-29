# ////////////////////////////////////////////////////////////////
# //                     IMPORT STATEMENTS                      //
# ////////////////////////////////////////////////////////////////

import math
import sys
import time

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import *
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from functools import partial
from kivy.config import Config
from kivy.core.window import Window
from pidev.kivy import DPEAButton
from pidev.kivy import PauseScreen
from time import sleep
from threading import Thread
import RPi.GPIO as GPIO 
from pidev.stepper import stepper
from pidev.Cyprus_Commands import Cyprus_Commands_RPi as cyprus


# ////////////////////////////////////////////////////////////////
# //                      GLOBAL VARIABLES                      //
# //                         CONSTANTS                          //
# ////////////////////////////////////////////////////////////////
START = True
STOP = False
UP = False
DOWN = True
ON = True
OFF = False
YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
CLOCKWISE = 0
COUNTERCLOCKWISE = 1
ARM_SLEEP = 2.5
DEBOUNCE = 0.10

lowerTowerPositions = [47, 48, 46, 49, 45]
upperTowerPositions = [59, 60, 58, 61, 57]


# ////////////////////////////////////////////////////////////////
# //            DECLARE APP CLASS AND SCREENMANAGER             //
# //                     LOAD KIVY FILE                         //
# ////////////////////////////////////////////////////////////////
class MyApp(App):

    def build(self):
        self.title = "Robotic Arm"
        return sm

Builder.load_file('main.kv')
Window.clearcolor = (.1, .1,.1, 1) # (WHITE)

cyprus.open_spi()

# ////////////////////////////////////////////////////////////////
# //                    SLUSH/HARDWARE SETUP                    //
# ////////////////////////////////////////////////////////////////

sm = ScreenManager()
arm = stepper(port=0, micro_steps=32, hold_current=20, run_current=20, accel_current=20, deaccel_current=20,
               steps_per_unit=25, speed=5)

# ////////////////////////////////////////////////////////////////
# //                       MAIN FUNCTIONS                       //
# //             SHOULD INTERACT DIRECTLY WITH HARDWARE         //
# ////////////////////////////////////////////////////////////////


def toggle_arm():
    global UP
    if UP:
        cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
    else:
        cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
    UP = not UP


def move_arm(pos):
    if pos == 0:
        arm.home(0)
    else:
        arm.start_go_to_position(pos / 5.0)


def move_arm_final(pos):
    if pos == 0:
        arm.home(0)
    else:
        arm.go_to_position(pos / 5.0)


def is_ball_off_lower():
    return (cyprus.read_gpio() & 0b0010) != 0


def is_ball_on_upper():
    return (cyprus.read_gpio() & 0b0001) == 0


def toggle_magnet():
    global ON
    if ON:
        cyprus.set_servo_position(2, 0.5)
    else:
        cyprus.set_servo_position(2, 1)
    ON = not ON


def home_arm():
    arm.home(0)


def try_lift(function, positions, lower):
    global ON
    count = 0
    while function():
        move_arm_final(positions[count])
        toggle_arm()
        sleep(1.5)
        if (lower and not function()) or not lower:
            toggle_magnet()
        toggle_arm()
        sleep(0.5)
        if not lower and function():
            toggle_magnet()
        sleep(1)
        if count < 4:
            count = count + 1
        else:
            count = 0
            home_arm()


# ////////////////////////////////////////////////////////////////
# //        DEFINE MAINSCREEN CLASS THAT KIVY RECOGNIZES        //
# //                                                            //
# //   KIVY UI CAN INTERACT DIRECTLY W/ THE FUNCTIONS DEFINED   //
# //     CORRESPONDS TO BUTTON/SLIDER/WIDGET "on_release"       //
# //                                                            //
# //   SHOULD REFERENCE MAIN FUNCTIONS WITHIN THESE FUNCTIONS   //
# //      SHOULD NOT INTERACT DIRECTLY WITH THE HARDWARE        //
# ////////////////////////////////////////////////////////////////


class MainScreen(Screen):
    version = cyprus.read_firmware_version()
    armPosition = 0
    lastClick = time.clock()

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.initialize()

    def debounce(self):
        processInput = False
        currentTime = time.clock()
        if (currentTime - self.lastClick) > DEBOUNCE:
            processInput = True
        self.lastClick = currentTime
        return processInput

    def toggleArm(self):
        toggle_arm()
        if UP:
            self.ids.armControl.text = "Lower Arm"
        else:
            self.ids.armControl.text = "Raise Arm"

    def toggleMagnet(self):
        toggle_magnet()
        if ON:
            self.ids.magnetControl.text = "Drop Ball"
        else:
            self.ids.magnetControl.text = "Hold Ball"
        
    def auto(self):
        global ON
        global UP
        temp_on = ON
        temp_up = UP
        ON = True
        toggle_magnet()
        UP = False
        toggle_arm()
        for i in range(0, 50):
            if is_ball_on_upper():
                break
            print("Please place ball on higher tower.")
            sleep(1)
        else:
            return
        try_lift(is_ball_on_upper, upperTowerPositions, False)
        try_lift(is_ball_off_lower, lowerTowerPositions, True)


        ON = not temp_on
        toggle_magnet()
        UP = not temp_up
        toggle_arm()
        move_arm_final(self.armPosition)

    def setArmPosition(self, position):
        self.armPosition = position
        move_arm(self.armPosition)
        self.ids.armControlLabel.text = 'Arm Position: ' + str(int(self.armPosition))
        
    def initialize(self):
        toggle_arm()
        toggle_magnet()
        home_arm()

    def resetColors(self):
        self.ids.armControl.color = YELLOW
        self.ids.magnetControl.color = YELLOW
        self.ids.auto.color = BLUE

    def quit(self):
        print("Exit")
        arm.free_all()
        GPIO.cleanup()
        GPIO.cleanup()
        cyprus.close()
        MyApp().stop()


sm.add_widget(MainScreen(name='main'))


# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////

MyApp().run()
