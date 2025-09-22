import numpy as np


# https://www.desmos.com/calculator/khkztixyeu
def super_sigmoid(inp, toe_x, toe_y, shoulder_x, shoulder_y):
    # clip
    inp = np.clip(inp, 0., 1.)
    toe_x = np.clip(toe_x, 0., 1.)
    toe_y = np.clip(toe_y, 0., 1.)
    shoulder_x = np.clip(shoulder_x, 0., 1.)
    shoulder_y = np.clip(shoulder_y, 0., 1.)

    # calculate straight line slope
    slope = (shoulder_y - toe_y) / (shoulder_x - toe_x)

    # toe
    if inp < toe_x:
        toe_pow = slope * toe_x / toe_y
        return toe_y * (inp / toe_x)**toe_pow

    # straight line
    if inp < shoulder_x:
        intercept = toe_y - (slope * toe_x)
        return slope * inp + intercept

    # shoulder
    shoulder_pow = -slope / (
        ((shoulder_x - 1.) / (1. - shoulder_x)**2.) * (1. - shoulder_y)
    )
    return (1. - (1. - (inp - shoulder_x) / (1. - shoulder_x))**shoulder_pow)  \
        * (1. - shoulder_y)  \
        + shoulder_y


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # plot parameters
    toe = [.402, .273]
    shoulder = [.664, .699]

    xs = np.arange(0., 1., .01)
    ys = np.vectorize(super_sigmoid)(
        xs, toe[0], toe[1], shoulder[0], shoulder[1])

    fig, ax = plt.subplots()
    ax.plot(xs, ys)

    ax.set(xlabel='normalized log of input', ylabel='normalized density',
           title='Super-Sigmoid for flim')
    ax.grid()

    plt.show()
