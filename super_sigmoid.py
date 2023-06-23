import numpy as np


def super_sigmoid(inp, toe_x, toe_y, shoulder_x, shoulder_y):
    # Clip
    inp = np.clip(inp, 0, 1)
    toe_x = np.clip(toe_x, 0, 1)
    toe_y = np.clip(toe_y, 0, 1)
    shoulder_x = np.clip(shoulder_x, 0, 1)
    shoulder_y = np.clip(shoulder_y, 0, 1)
    
    # Calculate straight line slope
    slope = (shoulder_y - toe_y) / (shoulder_x - toe_x)
    
    # Toe
    if inp < toe_x:
        toe_pow = slope * toe_x / toe_y
        return toe_y * (inp / toe_x)**toe_pow
    
    # Straight line
    if inp < shoulder_x:
        intercept = toe_y - (slope * toe_x)
        return slope * inp + intercept
    
    # Shoulder
    shoulder_pow = -slope / (((shoulder_x - 1.0) / (1.0 - shoulder_x)**2.0) * (1.0 - shoulder_y))
    return (1.0 - (1.0 - (inp - shoulder_x) / (1.0 - shoulder_x))**shoulder_pow) * (1.0 - shoulder_y) + shoulder_y


def demo_plot():
    import matplotlib.pyplot as plt
    
    # Plot parameters
    toe = [0.402, 0.273]
    shoulder = [0.664, 0.699]
    
    xs = np.arange(0.0, 1.0, 0.01)
    ys = np.vectorize(super_sigmoid)(xs, toe[0], toe[1], shoulder[0], shoulder[1])
    
    fig, ax = plt.subplots()
    ax.plot(xs, ys)
    
    ax.set(xlabel='normalized log of input', ylabel='normalized density',
           title='Super-Sigmoid for flim')
    ax.grid()
    
    plt.show()
