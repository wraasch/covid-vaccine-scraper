import json, requests
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone


def vaccine_appointments():
    # Response link was acquired from the LA County signup page (http://publichealth.lacounty.gov/acd/ncorona2019/vaccine/hcwsignup/pods/)
    # To view data source, load above link, and view NETWORK>RESPONSE tab for pod-data.js in your browser developer console
    response = requests.get('http://publichealth.lacounty.gov/acd/ncorona2019/js/pod-data.js')
    # Clean response text and convert to JSON
    cleaned_response = response.text.split('var unfiltered = ')[1]
    json_response = json.loads(cleaned_response)
    available_clinics = []

    # Filter only available clinics
    for j in json_response:
        # Only include clinics with clickable appointment links
        # Exclude clinics with 'no appointments are currently available' comment
        if j['link'] and 'no appointments are currently available' not in j['comments']:
            available_clinics.append(j)

    for a in available_clinics:
        # If clinic doesn't have a name, find it's parent record and join child to parent
        if not a['name']:
            parent = [j for j in json_response if j['id'] == a['xParent']]
            if parent:
                a['name'] = parent[0]['name']
                a['addr1'] = parent[0]['addr1']
                a['addr2'] = parent[0]['addr2']
            else:
                available_clinics.remove(a)
        # Derive zip code from addr2 header for searchability
        a['zip'] = a['addr2'][-5:]
        # If appointment date/time is listed, combine into comments
        if a['date'] or a['time']:
            a['comments'] = '%s, %s<br>%s' % (a['date'], a['time'], a['comments'])
        if not a['comments']:
            a['comments'] = 'Registration link is open'

    cache.set('vaccines_lacounty', available_clinics, None)

    # Set Last Updated timestamp to now
    last_updated = timezone.now()
    cache.set('vaccines_lacounty_timestamp', last_updated, None)

    return available_clinics, last_updated


class Command(BaseCommand):
    
    help = 'Scrape vaccine appointment sites'
    
    def handle(self, *args, **options):
        vaccine_appointments()
