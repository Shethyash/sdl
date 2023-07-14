import datetime
import json
import os.path

import pandas as pd
import numpy as np
import keras
import requests
import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from nodes.models import Nodes, Feeds, CropImage
from .forms import RegisterForm, ImageUploadForm, CSVImportForm


# Create your views here.

def feeds_preprocess(node_id, lws, c_time):
    rec = Feeds.objects.filter(node_id=node_id).order_by('-id').values()
    if not rec: 
        return {'duration': 0, 'event': 0}
    last_rec = rec[0]
    timediff = c_time - last_rec['created_at']
    timediff = int((timediff.total_seconds()) / 3600)
    last_lws = last_rec['LWS']
    if (last_lws >= 46000) and (lws < 46000):
        # event starting point
        # TODO : change in last param and add duration in current param
        # duration = timediff
        # event = 1
        return {'duration': timediff, 'event': 1}
    elif (last_lws < 46000) and (lws >= 46000):
        # end of event, change in new param
        duration = last_rec['duration'] + timediff
        # event = 0
        return {'duration': duration, 'event': 0}
    else:
        # put blank parameter
        if last_rec['event'] == 1:
            duration = last_rec['duration'] if last_rec['duration'] is not None else 0 + timediff
        else:
            duration = last_rec['duration'] if last_rec['duration'] is not None else 0
        event = last_rec['event'] if last_rec['event'] else 0
        # print(duration, last_rec['event'])
        return {'duration': duration, 'event': event}


def get_gwc(sm):
    file = open(os.path.join('static', "csv/calibration_data.csv"))
    csv_reader = csv.reader(file)
    rows = []
    for row in csv_reader:
        rows.append({'content': float(row[0]), 'frequency': float(row[1])})

    file.close()
    for it in range(0, len(rows) - 1):
        if rows[it]['frequency'] > sm > rows[it + 1]['frequency']:
            a = rows[it]['frequency'] - rows[it + 1]['frequency']
            b = rows[it + 1]['content'] - rows[it]['content']
            c = a * (rows[it + 1]['frequency']) + b * (rows[it + 1]['content'])
            gwc = (c - (b * sm)) / a
            # print(rows[it][0], gwc)
            return gwc
    return 0


@csrf_exempt
def store_feeds(request):
    if request.method == "POST":
        # store data to db
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        print(json.dumps(body))
        node = Nodes.objects.get(id=body['node_id'])
        if node:
            c_time = datetime.datetime.now(tz=timezone.utc)
            # get leaf wetness duration
            dura = feeds_preprocess(body['node_id'], body['LWS'], c_time)
            print(dura)
            gwc = get_gwc(body['soil_moisture'])
            # get predication for current data
            pred = predict_data(body['temperature'], body['humidity'], body['soil_temperature'], dura['duration'], 0.0)
            f_data = Feeds(
                node_id=body['node_id'],
                temperature=body['temperature'],
                humidity=body['humidity'],
                LWS=body['LWS'],
                soil_temperature=body['soil_temperature'],
                soil_moisture=body['soil_moisture'],
                battery_status=body['battery_status'],
                duration=dura['duration'],
                GWC=gwc,
                event=dura['event'],
                powdery_mildew=pred['powdery_mildew'],
                anthracnose=pred['anthracnose'],
                root_rot=pred['root_rot'],
                irrigation=pred['irrigation'],
            )

            f_data.save()
            node.last_feed_time = c_time
            node.save()
            return HttpResponse(json.dumps(body))

    return HttpResponse()


@login_required
def get_feeds(request, node_id):
    data = Feeds.objects.filter(node_id=node_id)
    node = Nodes.objects.get(id=node_id)
    return render(request, 'nodes/get_feeds.html', {'data': data, 'node': node, 'node_id': node_id})


@login_required
def get_feeds_table(request, node_id):
    page_num = int(request.GET.get('page', 1))
    if page_num <= 1:
        page_num = 1
    data = Feeds.objects.filter(node_id=node_id).order_by('-id')
    paginator = Paginator(data, 12)
    node = Nodes.objects.get(id=node_id)
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'nodes/feed_table.html', {'data': page_obj, 'node': node, 'node_id': node_id})


@login_required
def export_feeds_csv(request, node_id):
    # Define the response object with appropriate headers for a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="node_{node_id}_feeds.csv"'

    # Create a CSV writer and write the header row
    writer = csv.writer(response)
    writer.writerow(['Id', 'Node_id', 'Temperature', 'Humidity',
                    'Soil Temperature', 'Soil Moisture', 'LWS', 'Battery', 'Created_at'])

    # Fetch the data and write it to the CSV file
    data = Feeds.objects.filter(node_id=node_id).order_by('-id')

    for feed in data:
        writer.writerow([feed.id, feed.node_id, feed.temperature, feed.humidity, feed.soil_temperature,
                        feed.soil_moisture, feed.LWS, feed.battery_status, feed.created_at.strftime("%b %d, %Y %H:%M:%S")])

    return response


@login_required
def node_list(request):
    # print(predict_data(27.378, 88.05571, 18.84202, 0.5522222222222222, 0.0))
    get_gwc(9687.3379)
    data = Nodes.objects.filter(user_id=request.user.id)
    date = timezone.now()
    for i in data:
        if (i.last_feed_time is None) or i.last_feed_time is not None and date > i.last_feed_time + datetime.timedelta(
                minutes=30):
            i.status = False
    # fetch_data_from_thing_speak(request.user.id)
    return render(request, 'nodes/list.html', {'data': data, 'user_id': request.user.id})


@login_required
def node_particuler_list(request, user_id):
    if not request.user.is_superuser:
        return redirect(to='/get_all_users/')

    data = Nodes.objects.filter(user_id=user_id)
    date = timezone.now()
    for i in data:
        if (i.last_feed_time is None) or i.last_feed_time is not None and date > i.last_feed_time + datetime.timedelta(
                minutes=30):
            i.status = False
    # fetch_data_from_thing_speak(request.user.id)
    return render(request, 'nodes/list.html', {'data': data, 'user_id': user_id})


class CrudNodes(View):
    form_class = RegisterForm
    template_name = 'nodes/register.html'

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if not request.user.is_authenticated:
            return redirect(to='/')

        # else process dispatch as it otherwise normally would
        return super(CrudNodes, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        node_id = int(request.GET.get("id", 0))
        # print(node_id)
        user_id = int(request.GET.get("user_id", 0))
        # print(user_id)
        if node_id != 0:
            data = Nodes.objects.get(id=node_id)
            form = self.form_class(instance=data)
        else:
            form = self.form_class()
        return render(request, self.template_name, {'form': form, 'node_id': node_id, 'user_id': user_id})

    def post(self, request):
        node_id = int(request.POST.get('node_id', 0))
        # print(node_id)
        user_id = int(request.POST.get('user_id', 0))
        # print(user_id)
        if node_id != 0:
            data = Nodes.objects.get(id=node_id)
            form = self.form_class(request.POST, instance=data)
            msg = 'Node Edited successfully'
        else:
            form = self.form_class(request.POST)
            msg = 'Node created successfully'

        if form.is_valid():
            node = form.save(commit=False)
            #node.user_id = request.user.id
            if node.user_id == 0:
                node.user_id = user_id
            if not node.thing_speak_fetch:
                node.channel_id = 0
            node.save()

            messages.success(request, msg)
            if node.user_id == request.user.id:
                return redirect(to='nodes')
            else:
                return redirect(to='/nodes/user_nodes/' + str(node.user_id))

        return render(request, self.template_name, {'form': form})


@login_required
def crop_image_upload(request, node_id):
    form_class = ImageUploadForm
    if request.method == "POST":
        print(request.POST, request.FILES)
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            crop_image = form.save(commit=False)
            crop_image.node_id = node_id
            crop_image.save()
        messages.success(request, 'Image Upload successfully.')
        return redirect(to='nodes')
    return render(request, 'nodes/image_upload.html', {'form': form_class, 'node_id': node_id})


@login_required
def crop_image_gallery(request, node_id):
    data = CropImage.objects.filter(node_id=node_id)
    node = Nodes.objects.get(id=node_id)
    return render(request, 'nodes/image_gallery.html', {'data': data, 'node': node, 'node_id': node_id})


@login_required
def delete_node(request, node_id):
    # TODO: complete delete feeds code
    node = Nodes.objects.get(id=node_id)
    Feeds.objects.filter(node_id=node_id).delete()
    node.delete()
    messages.success(request, "Node deleted successfully.")
    # return redirect(to='nodes')
    if node.user_id == request.user.id:
        return redirect(to='nodes')
    else:
        return redirect(to='/nodes/user_nodes/' + str(node.user_id))


@login_required
def get_chart_data(request, node_id):
    data = Feeds.objects.filter(node_id=node_id)
    res = serializers.serialize('json', data)
    return HttpResponse(res, content_type="application/json")


def fetch_data_from_thing_speak(user_id):
    all_channel = Nodes.objects.filter(user_id=user_id)
    try:
        for channel in all_channel:
            if channel.channel_id is None:
                continue
            last_feed = "https://api.thingspeak.com/channels/" + \
                str(channel.channel_id) + "/feeds.json"
            lf_query = {'api_key': channel.node_api_key, 'minutes': 30}
            response = requests.get(last_feed, lf_query)
            data = response.json()
            print(data)
            if data['channel']['last_entry_id'] != channel.last_feed_entry:
                # fetch feeds
                # new_feeds = data['channel']['last_entry_id'] - channel.last_feed_entry
                # url = "https://api.thingspeak.com/channels/" + str(channel.id) + "/feeds.json"
                # query = {'api_key': channel.last_entry_id,
                #          'results': new_feeds,
                #          'minutes': 30}
                # response = requests.get(url, query)
                # feeds = response.json()
                for feed in data['feeds']:
                    print(feed)
                    # if type(feed['field5']) != int:
                    #     continue
                    Feeds.objects.create(
                        node_id=channel.id,
                        entry_id=feed['entry_id'],
                        temperature=feed['field1'],
                        humidity=feed['field2'],
                        LWS=feed['field4'],
                        soil_temperature=feed['field3'],
                        soil_moisture=feed['field5'],
                        battery_status=feed['field6'],
                        created_at=feed['created_at']
                    )

                # update channel
                channel.last_feed_entry = data['channel']['last_entry_id']
                channel.updated_at = timezone.now()
                channel.save()

    except Nodes.DoesNotExist:
        pass


# TODO : image storage in drive
# TODO : backup process
# TODO : 2 way communication


def predict_data(at, ah, st, lwd, sm):
    arr = [[at, ah, st, lwd, sm]]
    np_arr = np.array(arr)
    df = pd.DataFrame(np_arr,
                      columns=["Ambient_Temperature", "Ambient_Humidity", "Soil_Temperature", "Leaf_Wetness_Duration",
                               "Soil_Moisture"])
    model = keras.models.load_model(os.path.join('static', "models/demo_model.h5"))
    # print(df)
    pred = model.predict(df)
    # print(pred[0], pred[1])
    # return {'powdery_mildew': 0, 'anthracnose': 0, 'root_rot': 0, 'irrigation': 1}
    return {'powdery_mildew': pred[0][0][0], 'anthracnose': pred[0][0][1], 'root_rot': pred[0][0][2],
            'irrigation': pred[1][0][0]}


@login_required
def import_csv(request, node_id):
    form_class = CSVImportForm
    form = form_class()
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Invalid form.")
            return redirect(to='nodes')

        node = Nodes.objects.get(id=node_id)
        if not node:
            messages.error(request, "Node not found.")
            return redirect(to='nodes')

        csv_file = request.FILES['csv_file']
        df = pd.read_csv(csv_file)

        header_set = set(['temperature', 'humidity', 'LWS', 'soil_temperature',
                         'soil_moisture', 'battery_status', 'created_at'])

        # check if csv file has exactly same columns headers
        if not set(df.columns) == header_set:
            messages.error(request, "Invalid csv file.")
            return redirect(to='nodes')

        # Insert data into feeds collection
        records = df.to_dict(orient='records')

        # bulk create feed data with adding node id
        for record in records:
            record['node_id'] = node_id
        Feeds.objects.bulk_create([Feeds(**record) for record in records])

        messages.success(request, "data imported successfully.")
        # return redirect(to='nodes')
        if node.user_id == request.user.id:
            return redirect(to='nodes')
        else:
            return redirect(to=f'/nodes/user_nodes/{node.user_id}')

    return render(request, 'nodes/import_csv.html', {'form': form, 'node_id': node_id})
