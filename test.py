import argparse
import importlib
import os
import sys
import threading
import time

import numpy as np
import skimage.transform
import skimage.io
import panel as pn

import core
import layout as lt
import sym
import util

import matplotlib
matplotlib.use('Qt5Agg')
matplotlib.rcParams['toolbar'] = 'None'

import matplotlib.pyplot as plt
plt.ion()

fig = None

def differ(fn_im1, fn_im2):

    global fig
    global axes
    if fig is None:
        fig = plt.figure(num="update reference image? (y/n)", figsize=(9,3))
        fig.canvas.manager.window.move(10, 100)
        axes = fig.subplots(1, 3)

    im1 = skimage.io.imread(fn_im1)[:,:,0:3] if os.path.exists(fn_im1) else None
    im2 = skimage.io.imread(fn_im2)[:,:,0:3] if os.path.exists(fn_im2) else None
    
    difference = None

    if im1 is None:
        difference = f"im1 {fn_im1} does not exist"
    elif im2 is None:
        difference = f"im2 {fn_im2} does not exist"
    elif im1.shape != im2.shape:
        difference = f"image shapes {im1.shape} {im2.shape} differ"
    elif not (im1 - im2 == 0).all():
        difference = f"images differ"

    if difference:

        print(difference)

        keypress = None
        def on_keypress(event):
            nonlocal keypress
            keypress = event.key
        fig.canvas.mpl_connect("key_press_event", on_keypress)

        def show(i, im, name):
            if im is not None:
                h, w = im.shape[:2]
                axes[i].imshow(im, extent=[0, w, 0, h])
            axes[i].set_title(name.split("/")[-1], fontsize=10)
            axes[i].axis("off")
            axes[i].set_anchor("N")
            #axes[i].set_aspect("auto")

        show(0, im1, fn_im1)
        show(1, im2, fn_im2)
        if im1 is not None and im2 is not None:
            im2 = skimage.transform.resize(im2.astype(float), im1.shape[0:2])
            diff = abs(im2-im1).astype(int)
            show(2, diff, "diff")

        plt.tight_layout()
        plt.waitforbuttonpress()

        return keypress == "y"


    else:
        print("images are identical")

    return difference



if __name__ == "__main__":

    failures = 0
    successes = 0

    class FE:
        pass
    fe = FE()
    fe.session = core.MathicsSession()

    parser = argparse.ArgumentParser(description="Mathics3 graphics test")
    parser.add_argument("files", type=str, default=None, nargs="*")
    args = parser.parse_args()

    for fn in args.files:

        if fn in util.methods:
            util.switch_method(fn)
            continue

        fn_m = fn.replace(".png", ".m")
        fn_ref = fn.replace(".m", ".png")
        fn_test = "/tmp/test.png"

        print(f"=== {fn_m}")

        if os.path.exists(fn_test):
            os.remove(fn_test)

        fe.test_image = fn_test
        with open(fn_m) as f:
            s = f.read()
        expr = fe.session.parse(s)
        expr = expr.evaluate(fe.session.evaluation)
        layout = lt.expression_to_layout(fe, expr)

        # TODO: WIP
        # ff formats too wide, so fix that first
        #layout.save(f"/tmp/{fn_m.split('/')[-1]}-test.png")
        #

        if update := differ(fn_ref, fn_test):
            failures += 1
            if update:
                print(f"updating reference image {fn_ref}")
                with open(fn_test, "rb") as f_test:
                    img_data = f_test.read()
                    with open(fn_ref, "wb") as f_ref:
                        f_ref.write(img_data)
        else:
            successes += 1

    print(f"=== {successes} successes, {failures} failures")                    
