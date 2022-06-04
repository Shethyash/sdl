from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from csv import DictWriter
import json
from .models import Nodes, Feeds
from django.http import HttpResponse
# Create your views here.


@csrf_exempt
def store_feeds(request):

    if request.method == "POST":
        # store data to db
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        print(json.dumps(body))
        f_data = Feeds(
            node_id=body['node_id'],
            temperature=body['temperature'],
            humidity=body['humidity'],
            LWS=body['LWS'],
            soil_temperature=body['soil_temperature'],
            soil_moisture=body['soil_moisture'],
            battery_status=body['battery_status'])

        f_data.save()
        return HttpResponse(json.dumps(body))

    return HttpResponse()


def get_feeds(request):
    if request.method == "GET":
        id = request.GET.get("id")
        data = Feeds.objects.filter(node_id=id)
        return render(request, 'get_feeds.html', {'data': data})


def node(request):
    data = Nodes.objects.filter(user_id=request.user.id)
    return render(request, 'nodes/list.html', {'data': data})


def nodereg(request):
    if request.method == "POST":
        Name = request.POST.get('name')
        Status = request.POST.get('status')
        Description = request.POST.get('desc')
        Latitude = request.POST.get('latitude')
        Longitude = request.POST.get('longitude')

        node_data = Nodes(
            name=Name,
            user_id=request.user.id,
            status=Status,
            description=Description,
            latitude=Latitude,
            longitude=Longitude
        )
        node_data.save()
        return redirect('/nodes')

    return render(request, 'nodes/reg_node.html')


def edit_node(request):
    id = request.GET.get("id")
    data = Nodes.objects.get(id=id)
    return render(request, 'nodes/reg_node.html', {'data': data})
