import logging
import requests

import antares_client
from antares_client.search import get_by_ztf_object_id
from astropy.time import Time, TimezoneInfo
from crispy_forms.layout import Div, Fieldset, Layout, HTML
from django import forms
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import marshmallow

from tom_alerts.alerts import GenericBroker, GenericQueryForm, GenericAlert
from tom_targets.models import Target, TargetName

logger = logging.getLogger(__name__)

ANTARES_BASE_URL = 'https://antares.noirlab.edu'
ANTARES_API_URL = 'https://api.antares.noirlab.edu'
ANTARES_TAG_URL = ANTARES_API_URL + '/v1/tags'


def get_available_tags(url: str = ANTARES_TAG_URL):
    response = requests.get(url).json()
    tags = response.get('data', {})
    if response.get('links', {}).get('next'):
        return tags + get_available_tags(response['links']['next'])
    return tags


def get_tag_choices():
    tags = get_available_tags()
    return [(s['id'], s['id']) for s in tags]


# class ConeSearchWidget(forms.widgets.MultiWidget):

#     def __init__(self, attrs=None):
#         if not attrs:
#             attrs = {}
#         _default_attrs = {'class': 'form-control col-md-4', 'style': 'display: inline-block'}
#         attrs.update(_default_attrs)
#         print(attrs)
#         ra_attrs.update({'placeholder': 'Right Ascension'})
#         print(ra_attrs)

#         _widgets = (
#             forms.widgets.NumberInput(attrs=ra_attrs),
#             forms.widgets.NumberInput(attrs=attrs.update({'placeholder': 'Declination'})),
#             forms.widgets.NumberInput(attrs=attrs.update({'placeholder': 'Radius (degrees)'}))
#         )

#         super().__init__(_widgets, attrs)

#     def decompress(self, value):
#         return [value.ra, value.dec, value.radius] if value else [None, None, None]


# class ConeSearchField(forms.MultiValueField):
#     widget = ConeSearchWidget

#     def __init__(self, *args, **kwargs):
#         fields = (forms.FloatField(), forms.FloatField(), forms.FloatField())
#         super().__init__(fields=fields, *args, **kwargs)

#     def compress(self, data_list):
#         return data_list


class ANTARESBrokerForm(GenericQueryForm):

    #define form content
    
    ztfid = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={'placeholder': 'ZTF object id, e.g. ZTF19aapreis'})
        )

    tag = forms.MultipleChoiceField(required=False,choices=get_tag_choices)

    nobs__gt = forms.IntegerField(
        required=False,
        label='Detections Lower',
        widget=forms.TextInput(attrs={'placeholder': 'Min number of measurements'})
    )
    nobs__lt = forms.IntegerField(
        required=False,
        label='Detections Upper',
        widget=forms.TextInput(attrs={'placeholder': 'Max number of measurements'})
    )
    ra = forms.FloatField(
        required=False,
        label='RA',
        widget=forms.TextInput(attrs={'placeholder': 'RA (Degrees)'}),
        min_value=0.0
    )
    dec = forms.FloatField(
        required=False,
        label='Dec',
        widget=forms.TextInput(attrs={'placeholder': 'Dec (Degrees)'}),
        min_value=0.0
    )
    sr = forms.FloatField(
        required=False,
        label='Search Radius',
        widget=forms.TextInput(attrs={'placeholder': 'radius (Degrees)'}),
        min_value=0.0
    )
    mjd__gt = forms.FloatField(
        required=False,
        label='Min date of alert detection ',
        widget=forms.TextInput(attrs={'placeholder': 'Date (MJD)'}),
        min_value=0.0
    )
    mjd__lt = forms.FloatField(
        required=False,
        label='Max date of alert detection',
        widget=forms.TextInput(attrs={'placeholder': 'Date (MJD)'}),
        min_value=0.0
    )
    mag__min = forms.FloatField(
        required=False,
        label='Min magnitude of the latest alert',
        widget=forms.TextInput(attrs={'placeholder': 'Min Magnitude'}),
        min_value=0.0
    )
    mag__max = forms.FloatField(
        required=False,
        label='Max magnitude of the latest alert',
        widget=forms.TextInput(attrs={'placeholder': 'Max Magnitude'}),
        min_value=0.0
    )
    esquery = forms.JSONField(
        required=False,
        label='Elastic Search query in JSON format',
        widget=forms.TextInput(attrs={'placeholder': '{"query":{}}'}),
    )


    # cone_search = ConeSearchField()
    # api_search_tags = forms.MultipleChoiceField(choices=get_tag_choices)

    # TODO: add section for searching API in addition to consuming stream

    # TODO: add layout
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            self.common_layout,
            HTML('''
                <p>
                Users can query objects in the ANTARES database using one of the following 
                three methods: 1. an object ID by ZTF, 2. a simple query form with constraints
                of object brightness, position, and associated tag, 3. an advanced query with
                Elastic Search syntax.
            </p>
            '''),
            HTML('<hr/>'),
            HTML('<p style="color:blue;font-size:30px">Query by object name</p>'),
            Fieldset(
                 'ZTF object ID',
                 'ztfid'
            ),
            HTML('<hr/>'),
            HTML('<p style="color:blue;font-size:30px">Simple query form</p>'),
            Fieldset(
                'Alert timing',
                Div(
                    Div(
                        'mjd__gt',
                        css_class='col',
                    ),
                    Div(
                        'mjd__lt',
                        css_class='col',
                    ),
                    css_class='form-row'
                    )
                ),
            Fieldset(
                'Number of measurements',
                Div(
                    Div(
                        'nobs__gt',
                        css_class='col',
                    ),
                    Div(
                        'nobs__lt',
                        css_class='col',
                    ),
                    css_class='form-row',
                )
            ),
            Fieldset(
                'Brightness of the latest alert',
                Div(
                    Div(
                        'mag__min',
                        css_class='col',
                    ),
                    Div(
                        'mag__max',
                        css_class='col',
                    ),
                  css_class='form-row'
               )
            ),
            Fieldset(
                'Cone Search',
                Div(
                    Div(
                        'ra',
                        css_class='col'
                    ),
                    Div(
                        'dec',
                        css_class='col'
                    ),
                    Div(
                        'sr',
                        css_class='col'
                    ),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'View Tags',
                'tag'
            ),
            HTML('<hr/>'),
            HTML('<p style="color:blue;font-size:30px">Advanced query</p>'),
            Fieldset(
                 '',
                 'esquery'
            ),
            HTML('''
                <p>
                Please see <a href="https://noao.gitlab.io/antares/client/tutorial/searching.html">ANTARES Documentation</a>
                for a detailed description of advanced searches.
                </p>
            ''')
            # HTML('<hr/>'),
            # Fieldset(
            #     'API Search',
            #     'api_search_tags'
            # )
        )
            
    def clean(self):
        cleaned_data = super().clean()

        # Ensure all cone search fields are present
        if any(cleaned_data[k] for k in ['ra', 'dec', 'sr']) and not all(cleaned_data[k] for k in ['ra', 'dec', 'sr']):
            raise forms.ValidationError('All of RA, Dec, and Search Radius must be included to perform a cone search.')
        #default value for cone search
        if not all(cleaned_data[k] for k in ['ra', 'dec', 'sr']):
            cleaned_data['ra'] = 180.
            cleaned_data['dec'] = 0.
            cleaned_data['sr'] = 180.
        
        # Ensure alert timing constraints have sensible values
        if all(cleaned_data[k] for k in ['mjd__lt', 'mjd__gt']) and cleaned_data['mjd__lt'] <= cleaned_data['mjd__gt']:
            raise forms.ValidationError('Min date of alert detection must be earlier than max date of alert detection.')

        # Ensure number of measurement constraints have sensible values
        if all(cleaned_data[k] for k in ['nobs__lt', 'nobs__gt']) and cleaned_data['nobs__lt'] <= cleaned_data['nobs__gt']:
            raise forms.ValidationError('Min number of measurements must be smaller than max number of measurements.')

        # Ensure magnitude constraints have sensible values
        if all(cleaned_data[k] for k in ['mag__min', 'mag__max']) and cleaned_data['mag__max'] <= cleaned_data['mag__min']:
            raise forms.ValidationError('Min magnitude must be smaller than max magnitude.')

#        # Ensure using either a stream or the advanced search form
#        if not (cleaned_data['tag'] or cleaned_data['esquery']):
#            raise forms.ValidationError('Please either select tag(s) or use the advanced search query.')

        # Ensure using either a stream or the advanced search form
        if not (cleaned_data['ztfid'] or cleaned_data['tag'] or cleaned_data['esquery']):
            raise forms.ValidationError('Please either enter the ZTF ID, or select tag(s), or use the advanced search query.')

        
        return cleaned_data

        

class ANTARESBroker(GenericBroker):
    name = 'ANTARES'
    form = ANTARESBrokerForm

    @classmethod
    def alert_to_dict(cls, locus):
        """
        Note: The ANTARES API returns a Locus object, which in the TOM Toolkit
        would otherwise be called an alert.

        This method serializes the Locus into a dict so that it can be cached by the view.
        """
        return {
            'locus_id': locus.locus_id,
            'ra': locus.ra,
            'dec': locus.dec,
            'properties': locus.properties,
            'tags': locus.tags,
            # 'lightcurve': locus.lightcurve.to_json(),
            'catalogs': locus.catalogs,
            'alerts': [{
                'alert_id': alert.alert_id,
                'mjd': alert.mjd,
                'properties': alert.properties
            } for alert in locus.alerts]
        }

    def fetch_alerts(self, parameters: dict) -> iter:
        tags = parameters['tag']
        nobs_gt = parameters['nobs__gt']
        nobs_lt = parameters['nobs__lt']
        sra = parameters['ra']
        sdec = parameters['dec']
        ssr = parameters['sr']
        mjd_gt = parameters['mjd__gt']
        mjd_lt = parameters['mjd__lt']
        mag_min = parameters['mag__min']
        mag_max = parameters['mag__max']
        elsquery = parameters['esquery']
        ztfid = parameters['ztfid']
        if ztfid:
            query = {
                "query":{
                    "bool":{
                        "must":[
                            {
                                "match":{
                                    "properties.ztf_object_id": ztfid
                                }
                            }
                        ]
                    }
                }
            }
        elif elsquery:
            query = elsquery
        else:
            query = {
                "query": {
                    "bool": {
                        "filter":[
                            {
                                "range": {
                                    "properties.num_mag_values": {
                                        "gte": nobs_gt,
                                        "lte": nobs_lt,
                                    }
                                }
                            },
                            {
                                "range": {
                                    "properties.newest_alert_observation_time": {
                                        "lte": mjd_lt,
                                    }
                                }
                            },
                            {
                                "range": {
                                    "properties.oldest_alert_observation_time": {
                                        "gte": mjd_gt,
                                    }
                                }
                            },
                            {
                                "range": {
                                    "properties.newest_alert_magnitude": {
                                        "gte": mag_min,
                                        "lte": mag_max,
                                    }
                                }
                            },
                            {
                                "range": {
                                    "ra": {
                                        "gte": sra-ssr,
                                        "lte": sra+ssr,
                                    }
                                }
                            },
                            {
                                "range": {
                                    "dec": {
                                        "gte": sdec-ssr,
                                        "lte": sdec+ssr,
                                    }
                                }
                            },
                            {
                                "terms": {
                                    "tags": tags
                                }
                            }
                        ]
                    }
                }
            }
        loci = antares_client.search.search(query)
#        if ztfid:
#            loci = get_by_ztf_object_id(ztfid)
        alerts = []
        while len(alerts) < 20:
            try:
                locus = next(loci)
            except (marshmallow.exceptions.ValidationError, StopIteration):
                break
            alerts.append(self.alert_to_dict(locus))
        return iter(alerts)

    def fetch_alert(self, id):
        alert = get_by_ztf_object_id(id)
        return alert

    # TODO: This function
    def process_reduced_data(self, target, alert=None):
        pass

    def to_target(self, alert: dict) -> Target:
        target = Target.objects.create(
            name=alert['properties']['ztf_object_id'],
            type='SIDEREAL',
            ra=alert['ra'],
            dec=alert['dec'],
        )
        TargetName.objects.create(target=target, name=alert['locus_id'])
        if alert['properties'].get('horizons_targetname'):  # TODO: review if any other target names need to be created
            TargetName.objects.create(target=target, name=alert['properties'].get('horizons_targetname'))
        return target

    def to_generic_alert(self, alert):
        url = f"{ANTARES_BASE_URL}/loci/{alert['locus_id']}"
        timestamp = Time(
            alert['properties'].get('newest_alert_observation_time'), format='mjd', scale='utc'
        ).to_datetime(timezone=TimezoneInfo())
        return GenericAlert(
            timestamp=timestamp,
            url=url,
            id=alert['locus_id'],
            name=alert['properties']['ztf_object_id'],
            ra=alert['ra'],
            dec=alert['dec'],
            mag=alert['properties'].get('newest_alert_magnitude', ''),
            score=alert['alerts'][-1]['properties'].get('ztf_rb', '')
        )
