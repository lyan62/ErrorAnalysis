"""
congruency.py - Emiel van Miltenburg, 2017.

This is a Flask app designed to annotate image descriptions for the Flickr30K data.
All the annotation data is represented through dictionaries. This tool outputs them
as JSON files.

The JSON files map image indices to annotations. Those indices correspond to (0-indexed)
line numbers in val_images.txt. Each line contains the filename of an image.
"""


from __future__ import unicode_literals
from flask import Flask, url_for, request, render_template, redirect
import glob
import json
import os
from collections import defaultdict
import random
from datetime import datetime
import shutil

random.seed(42)
app = Flask(__name__)

# Set variables.
IMAGE_PATH = '/static/val_sd_v1-5_finetuned/top_images/'

def sort_by_clipscore():
    with open("static/val_sd_v1-5_finetuned/sd_v15_finetuned_val_clipscore.json", "r") as input_json:
        data = json.load(input_json)
        sorted_data = sorted(data.items(), key=lambda x: x[1]["RefCLIPScore"])
        validation_images = [x[0]+".jpg" for x in sorted_data]
        return validation_images

# Get image names.
# with open("static/val_sd_v1-5_finetuned/annotation/val_epoch0.json", "r") as f:
#     val_data =  json.load(f)
#     validation_images = [d["image_id"] + ".jpg" for d in val_data]
validation_images = sort_by_clipscore()
# for image in validation_images:
#     shutil.copy(os.path.join("/Users/wli/ErrorAnalysis/static/val_sd_v1-5_finetuned/images",  image), os.path.join("/Users/wli/ErrorAnalysis/static/val_sd_v1-5_finetuned/top_images",  image))
# Get generated sentences.
# generated_sentences = [d["caption"] for d in val_data]
img2idx = {img:i for i,img in enumerate(validation_images)}
idx2img = {i:img for i, img in enumerate(validation_images)}

# Load all the reference sentences.
with open("static/val_sd_v1-5_finetuned/annotation/sd_ann.json", "r") as input_json:
    val_ann = json.load(input_json)
    val_ann_dict = {x["image"]:x["caption"] for x in val_ann}
    references = defaultdict(list)
    for idx, image in enumerate(validation_images):
        references[img2idx[image]] = [c for c in val_ann_dict[image] if len(c.split()) <20][:2]
    generated_sentences = ["*"]*len(references)
    # for idx, d in enumerate(val_ann):
    #     if d["image"] in validation_images:
    #         references[img2idx[d["image"]]] = random.choices(d["caption"], k=2)

# Modify this number if you want to annotate only a subset:
total = 20#len(references) # Change len(reference) to e.g. 100
congruency = dict()

assert len(references) == len(validation_images)
assert len(references) == len(generated_sentences)
print("Successfully loaded the data.")

def congruency_indices(d,judgment):
    "Return indices from d for all items that have a particular judgment."
    return sorted(i for i,j in d.items() if j == judgment)

@app.route("/", methods=['GET'])
def main_page(i = 0):
    """
    Main page. Might be extended to quickly go to a particular image.
    Right now it's just useful to see how the template works.
    """
    # Start at the beginning.
    print(os.path.join(IMAGE_PATH, validation_images[i]))
    return render_template('index.html',
                            number=i,
                            total=total,
                            refs=references[i],
                            generated=generated_sentences[i],
                            image=IMAGE_PATH + validation_images[i])

@app.route('/congruency/',methods=['GET','POST'])
def check_congruency():
    "Annotate descriptions for congruency."
    # We'll make use of this global variable.
    global congruency
    
    # Start at the beginning.
    if request.method == 'GET':
        # Reset the congruency dict.
        print("Resetting congruency dict.")
        congruency = dict()
        # This variable corresponds to the first image.
        i=0
    
    # If we got a POST-request.
    else:
        number = request.form['number']
        congruency[number] = request.form['congruency']
        i = int(number) + 1
        with open('congruency_data.json','w') as f:
            json.dump(congruency,f)
        # If we are done, we don't need to go to the annotation page anymore.
        if i == total:
            return render_template('done.html',
                                    message="Done! Go to 'Load Congruency' to load the JSON file!")
    
    return render_template('congruency.html',
                           number=i,
                           total=total,
                           refs=references[i],
                           generated=generated_sentences[i],
                           image=IMAGE_PATH + validation_images[i])

@app.route('/load_congruency/',methods=['GET','POST'])
def load_congruency():
    "Load a specific congruency file"
    # This method modifies the global variable 'congruency' by loading JSON data.
    global congruency
    # Dictionaries with all images judged to be congruent/incongruent.
    global congruent
    global incongruent
    # Length of those dictionaries.
    global total_congruent
    global total_incongruent
    
    if request.method == 'POST':
        filename = request.form['filename']
        print(filename)
        with open(filename) as f:
            congruency = json.load(f)
            congruency = {int(i):judgment for i,judgment in congruency.items()}
            congruent = dict(enumerate(congruency_indices(congruency, 'congruent')))
            incongruent = dict(enumerate(congruency_indices(congruency, 'incongruent')))
            total_congruent = len(congruent)
            total_incongruent = len(incongruent)
        return render_template('load_congruency.html', loaded=True)
    return render_template('load_congruency.html')


@app.route('/inspect_congruent/',methods=['GET','POST'])
def inspect_congruent():
    "Inspect the data with a previous/next-button."
    if request.method == 'GET':
        idx = 0
    else:
        idx = int(request.form['number'])
        if request.form['target'] == 'next' and not idx == total_congruent:
            idx += 1
        elif request.form['target'] == 'previous' and not idx == 0:
            idx -= 1
    
    try:
        i = congruent[idx]
    except NameError:
        return render_template('done.html',
                                message="Please load the congruency data from disk.")
    return render_template('inspect_congruency.html',
                            task_url='/inspect_congruent/',
                            number=i,
                            congruency_index=idx,
                            total=total,
                            category_total=total_congruent,
                            refs=references[i],
                            generated=generated_sentences[i],
                            image=IMAGE_PATH + validation_images[i])

@app.route('/inspect_incongruent/',methods=['GET','POST'])
def inspect_incongruent():
    "Inspect the data with a previous/next-button."
    if request.method == 'GET':
        idx = 0
    else:
        idx = int(request.form['number'])
        if request.form['target'] == 'next' and not idx == total_incongruent:
            idx += 1
        elif request.form['target'] == 'previous' and not idx == 0:
            idx -= 1
    
    try:
        i = incongruent[idx]
    except NameError:
        return render_template('done.html',
                                message="Please load the congruency data from disk.")
    return render_template('inspect_congruency.html',
                            task_url='/inspect_incongruent/',
                            number=i,
                            congruency_index=idx,
                            total=total,
                            category_total=total_incongruent,
                            refs=references[i],
                            generated=generated_sentences[i],
                            image=IMAGE_PATH + validation_images[i])


@app.route('/categorize_incongruent/',methods=['GET','POST'])
def categorize_incongruent():
    "Categorize the incongruent descriptions according to different error categories."
    global incongruent_categories
    if request.method == 'GET':
        next_index = 0
        incongruent_categories = dict()
    else:
        # Get information about the categorized description.
        idx = int(request.form['number'])
        categorized = incongruent[idx]
        features = request.form.getlist('feature')
        print(features)
        incongruent_categories[categorized] = features
        # Write out the data.
        with open('incongruent_categorized.json','w') as f:
            json.dump(incongruent_categories, f)
        # Get the index for the next incongruent image.
        next_index = idx + 1
        if next_index == total_incongruent:
            # Show the user that we are finished.
            return render_template('done.html',
                                    message="Saved judgment data to file: incongruent_categorized.json")
    try:
        i = incongruent[next_index]
    except NameError:
        return render_template('done.html',
                                message="Please load the congruency data from disk.")
    return render_template('categorize_incongruent.html',
                            task_url='/categorize_incongruent/',
                            number=i,
                            congruency_index=next_index,
                            total=total,
                            category_total=total_incongruent,
                            refs=references[i],
                            generated=generated_sentences[i],
                            image=IMAGE_PATH + validation_images[i])


@app.route('/categorize_sd_errors/',methods=['GET','POST'])
def categorize_sd_errors():
    "Categorize the incongruent descriptions according to different error categories."

    # creaste sudo congruency data
    output_folder = os.path.join("/static/annotated")
    os.makedirs(output_folder, exist_ok=True)
    with open('sd_data.json', 'w') as f:
        sd_congruency = {i: "incongruent" for i in range(len(img2idx))}
        json.dump(sd_congruency, f)

    incongruent = dict(enumerate(congruency_indices(sd_congruency, 'incongruent')))
    congruent = dict(enumerate(congruency_indices(congruency, 'congruent')))
    total_congruent = len(congruent)
    total_incongruent = min(len(incongruent), total)

    global incongruent_categories
    if request.method == 'GET':
        next_index = 0
        incongruent_categories = dict()
    else:
        # Get information about the categorized description.
        idx = int(request.form['number'])
        categorized = sd_congruency[idx]
        features = request.form.getlist('feature')
        comments = request.form.get('textbox')
        incongruent_categories[idx] = {"categories": features, "comments": comments, "img":idx2img[idx]}
        print(features)
        print(incongruent_categories)
        # Write out the data.
        # Get the index for the next incongruent image.
        next_index = idx + 1
        if next_index == total:
            ts = round(datetime.now().timestamp())
            output_path = os.path.join(output_folder, "sd_categorized_%s.json" % str(ts))
            with open(output_path, 'w') as f:
                json.dump(incongruent_categories, f)
            # Show the user that we are finished.
            return render_template('done.html',
                                    message="Saved judgment data to file: %s" % output_path)
    try:
        i = incongruent[next_index]
    except NameError:
        return render_template('done.html',
                                message="Please load the congruency data from disk.")
    return render_template('categorize_sd_errors.html',
                            task_url='/categorize_sd_errors/',
                            number=i,
                            congruency_index=next_index,
                            total=total,
                            category_total=total_incongruent,
                            refs=references[i],
                            generated="",#generated_sentences[i],
                            image=IMAGE_PATH + validation_images[i])


if __name__ == '__main__':
    app.debug = True
    app.run()
