import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from nodes.models import Nodes, Feeds
from .forms import RegisterForm


# Create your views here.


# @login_required
@csrf_exempt
def store_feeds(request):
    if request.method == "POST":
        # store data to db
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
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
        return HttpResponse(json.dumps(body))

    return HttpResponse()


@login_required
def get_feeds(request, node_id):
    data = Feeds.objects.filter(node_id=node_id)
    return render(request, 'nodes/get_feeds.html', {'data': data})


@login_required
def node_list(request):
    data = Nodes.objects.filter(user_id=request.user.id)
    return render(request, 'nodes/list.html', {'data': data})


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
        node_id = request.GET.get("id", None)
        if node_id:
            data = Nodes.objects.get(id=node_id)
            form = self.form_class(instance=data)
        else:
            form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)

        if form.is_valid():
            node = form.save(commit=False)
            node.user_id = request.user.id
            node.save()

            messages.success(request, f'Node created successfully')
            return redirect(to='nodes')

        return render(request, self.template_name, {'form': form})
