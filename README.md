# Camera Label Dashboard

Image capture and labeling as a service for the Neoracer, on port 8082. Students capture frames from the car's camera, drag boxes on them, and the dashboard saves a YOLO-ready dataset for model training.

## Contents

- [Install](#install)
- [Service control](#service-control)
- [Workflow](#workflow)
- [Settings](#settings)
- [Dataset](#dataset)
- [Training parameters](#training-parameters)

## Install

On the car:

```
git clone https://github.com/Neobotics-Foundation-Inc/camlabel_dashboard.git
bash camlabel_dashboard/setup.sh
```

setup.sh points neoracer-camlabel.service at this checkout wherever it sits and copies nothing, so the repository can live anywhere the racecar user can read. A first install leaves the service stopped and disabled; start it with `bash setup.sh enable`. Dashboard: `http://<car-ip>:8082`.

Re-running setup.sh updates the unit and leaves the enable state alone: a running service restarts on the new code, a stopped one stays stopped.

## Service control

Run on the car, from the checkout:

| Command | Effect |
| --- | --- |
| `bash setup.sh` | install or update the unit; a first install does not start it |
| `bash setup.sh enable` | start now and at every boot |
| `bash setup.sh disable` | stop now and keep off across boots |
| `bash setup.sh restart` | restart; takes port 8082 back first |
| `bash setup.sh remove` | stop, disable, and uninstall the unit; keeps the dataset |

Enable, restart, and an update of a running service clear port 8082 first. A dashboard left over from an earlier install under a different unit name or directory, or any other service on 8082, is stopped through systemd; a `camlabel.py` started by hand is signalled directly. Without this the new instance would fail to bind and loop on `Restart=on-failure`.

After `remove`, the checkout and the dataset in `~/data/camlabel/` stay in place; `bash setup.sh` reinstalls.

## Workflow

Collection and labeling are separate stages:

1. Collect: Snap (button or spacebar) saves the current full-resolution frame to the unlabeled pool. Take as many as you want, fast.
2. Label: click or tap any thumbnail in the unlabeled section. Drag boxes on it (or tap one corner, then the other), the class field names each box, Enter or Save labels finishes it. The image moves from unlabeled to labeled and the next unlabeled image loads automatically. Prev, Next, or the arrow keys move through the unlabeled images. Delete image throws a bad shot away, saving with no boxes makes a negative example.
3. Labeled images show as thumbnails; click or tap one to see its boxes. Deleting a labeled image takes a press and hold on Hold to delete, since it cannot be undone.

The page works with a mouse, a touch screen or the keyboard, on a laptop, a tablet or a phone, in a light or a dark theme (the switch in the top bar).

## Settings

`camlabel.yaml` next to the script sets the live-preview resolution and jpeg quality sent to the browser (saved images are always the full camera frame). Restart the service after editing. Camera and preview resolutions show in the top bar.

## Dataset

Saved on the car in `~/data/camlabel/`, outside the code directory, so reinstalling or re-cloning camlabel leaves it alone. The tree is created at startup when missing:

- `unlabeled/uN.jpg`: collected frames waiting for labels (not part of the training set)
- `images/imgN.jpg`: the frame as captured, full camera resolution JPEG, no boxes burned in
- `labels/imgN.txt`: YOLO format, one line per box: `class_id cx cy w h`, normalized 0..1
- `classes.txt`: one class name per line, id = line number
- `train_params.txt`: training parameters saved from the dashboard

This layout trains directly with ultralytics by pointing a data.yaml at it.

A dataset from an install that kept it in a `dataset/` directory inside the checkout moves across on the next `bash setup.sh`. If `~/data/camlabel/` already holds files, the old directory is left untouched and reported instead, since image numbers from two datasets would collide.

## Training parameters

The bottom card holds the common YOLO parameters (model, epochs, batch, image size, learning rate, splits, augmentations), each with a short description. Save params writes them to `~/data/camlabel/train_params.txt`. A rough training time estimate for a Jetson Orin Nano updates live as values change.
