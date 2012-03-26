from django.conf.urls.defaults import *
from haystack.forms import FacetedSearchForm
from haystack.query import SearchQuerySet

from open_municipio.acts.models import Act
from open_municipio.acts.views import (ExtendedFacetedSearchView, ActListView, AgendaDetailView,
                                       DeliberationDetailView, InterpellationDetailView,
                                       InterrogationDetailView, MotionDetailView, ActDescriptionView)
from open_municipio.acts.views import ActAddTagsView, ActRemoveTagView
from voting.views import vote_on_object





act_dict = {
    'model': Act,
    'template_object_name': 'act',
    'allow_xmlhttprequest': 'true',
}

sqs = SearchQuerySet().facet('tags').facet('act_type').highlight()

urlpatterns = patterns('',
    url(r'^$', ActListView.as_view(),  name='om_act_list'),

    # faceted navigation
    url(r'^search/$', ExtendedFacetedSearchView(
            template='acts/act_search.html',
            form_class=FacetedSearchForm,
            searchqueryset=sqs,
        ),
        name='om_act_search'),

    # agendas
    url(r'^agendas/(?P<pk>\d+)/$', AgendaDetailView.as_view(),  name='om_agenda_detail'),
    url(r'^agendas/(?P<pk>\d+)/(?P<tab>documents)/$', AgendaDetailView.as_view(),  name='om_agenda_detail_documents'),
    url(r'^agendas/(?P<pk>\d+)/(?P<tab>emendations)/$', AgendaDetailView.as_view(),  name='om_agenda_detail_emendations'),
    # deliberations
    url(r'^deliberations/(?P<pk>\d+)/$', DeliberationDetailView.as_view(),  name='om_deliberation_detail'),
    url(r'^deliberations/(?P<pk>\d+)/(?P<tab>documents)/$', DeliberationDetailView.as_view(),  name='om_deliberation_detail_documents'),
    url(r'^deliberations/(?P<pk>\d+)/(?P<tab>emendations)/$', DeliberationDetailView.as_view(),  name='om_deliberation_detail_emendations'),
    # interpellations
    url(r'^interpellations/(?P<pk>\d+)/$', InterpellationDetailView.as_view(),  name='om_interpellation_detail'),
    url(r'^interpellations/(?P<pk>\d+)/(?P<tab>documents)/$', InterpellationDetailView.as_view(),  name='om_interpellation_detail_documents'),
    url(r'^interpellations/(?P<pk>\d+)/(?P<tab>emendations)/$', InterpellationDetailView.as_view(),  name='om_interpellation_detail_emendations'),
    # interrogations
    url(r'^interrogations/(?P<pk>\d+)/$', InterrogationDetailView.as_view(),  name='om_interrogation_detail'),
    url(r'^interrogations/(?P<pk>\d+)/(?P<tab>documents)/$', InterrogationDetailView.as_view(),  name='om_interrogation_detail_documents'),
    url(r'^interrogations/(?P<pk>\d+)/(?P<tab>emendations)/$', InterrogationDetailView.as_view(),  name='om_interrogation_detail_emendations'),
    # motions
    url(r'^motions/(?P<pk>\d+)/$', MotionDetailView.as_view(),  name='om_motion_detail'),
    url(r'^motions/(?P<pk>\d+)/(?P<tab>documents)/$', MotionDetailView.as_view(),  name='om_motion_detail_documents'),
    url(r'^motions/(?P<pk>\d+)/(?P<tab>emendations)/$', MotionDetailView.as_view(),  name='om_motion_detail_emendations'),
 )

## Tag management
urlpatterns += patterns('',
    url(r'^(?P<pk>\d+)/tags/add/$', ActAddTagsView.as_view(),  name='om_act_tags_add'),
    url(r'^(?P<act_pk>\d+)/tags/remove/(?P<tag_slug>[-\w]+)/$', ActRemoveTagView.as_view(),  name='om_act_tags_remove'),
    url(r'^(?P<object_id>\d+)/(?P<direction>up|down|clear)vote/?$', vote_on_object, act_dict),
)

## Act's description update
urlpatterns += patterns('',
    url(r'^(?P<pk>\d+)/description/update/$', ActDescriptionView.as_view(), name='om_act_description_update'),
)

