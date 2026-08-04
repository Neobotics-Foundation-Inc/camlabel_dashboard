# Camera Label Dashboard

Image capture and labeling as a service for the Neoracer, on port 8082. Students capture frames from the car's camera, drag boxes on them, and the dashboard saves a YOLO-ready dataset for model training.

## Install

From a laptop on the car's network:

```
scp -r neoracer_camlabel racecar@<car-ip>:~/camlabel
ssh racecar@<car-ip> 'bash ~/camlabel/setup.sh'
```

Dashboard: `http://<car-ip>:8082`. Runs as neoracer-camlabel.service, starts on boot.

## Workflow

Collection and labeling are separate stages:

1. Collect: Snap (button or spacebar) saves the current full-resolution frame to the unlabeled pool. Take as many as you want, fast.
2. Label: click any thumbnail in the unlabeled section. Drag boxes on it, the class field names each box, Enter or Save labels finishes it. The image moves from unlabeled to labeled and the next unlabeled image loads automatically. Skip moves on, Delete image throws a bad shot away, saving with no boxes makes a negative example.
3. Labeled images show as thumbnails with a click-to-view of their boxes.

## Settings

`camlabel.yaml` next to the script sets the live-preview resolution and jpeg quality sent to the browser (saved images are always the full camera frame). Restart the service after editing. Camera and preview resolutions show in the top bar.

## Dataset

Saved on the car in `~/camlabel/dataset/`:

- `unlabeled/uN.jpg`: collected frames waiting for labels (not part of the training set)
- `images/imgN.jpg`: the frame as captured, full camera resolution JPEG, no boxes burned in
- `labels/imgN.txt`: YOLO format, one line per box: `class_id cx cy w h`, normalized 0..1
- `classes.txt`: one class name per line, id = line number
- `train_params.txt`: training parameters saved from the dashboard

This layout trains directly with ultralytics by pointing a data.yaml at it.

## Training parameters

The bottom card holds the common YOLO parameters (model, epochs, batch, image size, learning rate, splits, augmentations), each with a short description. Save params writes them to `dataset/train_params.txt`. A rough training time estimate for a Jetson Orin Nano updates live as values change.
