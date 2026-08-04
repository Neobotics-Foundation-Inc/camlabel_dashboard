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

1. The camera card shows the live feed. Capture freezes the frame.
2. Click and drag on the image to box an object. The name typed in the class field goes into each box you drag. Undo box removes the last one.
3. Save writes the image and labels to disk and opens the review card showing exactly what was saved. Discard returns to live.
4. Review (top bar) opens a separate card for browsing all saved images with their boxes.

## Dataset

Saved on the car in `~/camlabel/dataset/`:

- `images/imgN.jpg`: the frame as captured, 640x480 JPEG, no boxes burned in
- `labels/imgN.txt`: YOLO format, one line per box: `class_id cx cy w h`, normalized 0..1
- `classes.txt`: one class name per line, id = line number
- `train_params.txt`: training parameters saved from the dashboard

This layout trains directly with ultralytics by pointing a data.yaml at it.

## Training parameters

The bottom card holds the common YOLO parameters (model, epochs, batch, image size, learning rate, splits, augmentations), each with a short description. Save params writes them to `dataset/train_params.txt`. A rough training time estimate for a Jetson Orin Nano updates live as values change.
