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

def feeds_preprocess(node_id, lws):
    last_rec = Feeds.objects.filter(node_id=node_id).first()
    if last_rec:
        last_lws = last_rec['LWS']
        if (last_lws >= 45000) and (lws < 45000):
            # change in last param and add duration in current param
            duration = last_rec['duration'] + 30  # add 30m in last duration
        elif (last_lws < 45000) and (lws >= 45000):
            # change in new param
            duration = last_rec['duration'] + 30  # add 30m in last duration
        else:
            # put blank parameter
            duration = last_rec['duration'] + \
                30 if last_rec['duration'] else last_rec['duration']
        return duration
    else:
        return 0


@csrf_exempt
def store_feeds(request):
    if request.method == "POST":
        # store data to db
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        node = Nodes.objects.get(id=body['node_id'])
        if node:
            # print(json.dumps(body))
            f_data = Feeds(
                node_id=body['node_id'],
                temperature=body['temperature'],
                humidity=body['humidity'],
                LWS=body['LWS'],
                soil_temperature=body['soil_temperature'],
                soil_moisture=body['soil_moisture'],
                battery_status=body['battery_status'])

            f_data.save()
            node.last_feed_time = datetime.datetime.now(tz=timezone.utc)
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
    writer.writerow(['Id', 'Node_id', 'Temperature', 'Humidity', 'Soil Temperature', 'Soil Moisture', 'LWS', 'Battery', 'Created_at'])

    # Fetch the data and write it to the CSV file
    data = Feeds.objects.filter(node_id=node_id).order_by('-id')
    
    for feed in data:
        writer.writerow([feed.id, feed.node_id, feed.temperature, feed.humidity, feed.soil_temperature, feed.soil_moisture, feed.LWS, feed.battery_status, feed.created_at.strftime("%b %d, %Y %H:%M:%S")])

    return response


@login_required
def node_list(request):
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


def predict_data():
    X = [[1.2, 1.3, 1.4, 1.5, 1.6]]
    x = np.array(X)
    df = pd.DataFrame(x, columns=['A', 'B', 'C', 'D', 'E'])
    model = keras.models.load_model(
        os.path.join('static', "models/demo_model.h5"))
    pred = model.predict(df)
    print(pred)


@login_required
def import_csv(request,node_id):
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

        header_set = set(['temperature','humidity','LWS','soil_temperature','soil_moisture','battery_status','created_at'])

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
        return redirect(to='nodes')

    return render(request, 'nodes/import_csv.html', {'form': form,'node_id': node_id})
