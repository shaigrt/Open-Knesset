'''
Api for auxilliary packages
'''
from tastypie.api import Api
from tastypie.constants import ALL
from tastypie.bundle import Bundle
import tastypie.fields as fields
from tagging.models import Tag, TaggedItem
from django.contrib.contenttypes.models import ContentType
from django.conf.urls.defaults import url

from apis.resources.base import BaseResource
from laws.models import Vote, Bill
from committees.models import CommitteeMeeting

from operator import attrgetter

class TagResource(BaseResource):
    ''' Tagging API
    '''
    class Meta:
        queryset = Tag.objects.all().order_by('name')
        allowed_methods = ['get']
        list_fields = [ 'id', 'name' ]

    TAGGED_MODELS = ( Vote, Bill, CommitteeMeeting )

    def obj_get_list(self, filters=None, **kwargs):
        all_tags = list(set().union(*[Tag.objects.usage_for_model(model) for model in self.TAGGED_MODELS]))
        all_tags.sort(key=attrgetter('name'))
        return all_tags

    def dehydrate(self, bundle):
        bundle.data['number_of_items'] = bundle.obj.items.count()
        return bundle

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/(?P<app_label>\w+)/(?P<object_type>\w+)/(?P<object_id>[0-9]+)/$' % self._meta.resource_name, self.wrap_view('get_object_tags'), name='tags-for-object'),
            url(r'^(?P<resource_name>%s)/(?P<app_label>\w+)/(?P<object_type>\w+)/(?P<object_id>[0-9]+)/(?P<related_name>[_a-zA-Z]\w*)/$' % self._meta.resource_name, self.wrap_view('get_related_tags'), name='related-tags'),
        ]

    def _create_response(self, request, objects):
        bundles = [] 
        for result in objects:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            bundles.append(bundle)

        return self.create_response(request, {'objects': bundles})

    def get_related_tags(self, request, **kwargs):
        """ Can be used to get all tags used by all CommitteeMeetings of a specific committee
        """
        # FIXME handle exception?
        ctype = ContentType.objects.get_by_natural_key(kwargs['app_label'], kwargs['object_type'])
        container = ctype.get_object_for_this_type(pk=kwargs['object_id'])

        related_objects = getattr(container, kwargs['related_name']).all()
        tags = Tag.objects.usage_for_queryset(related_objects)

        return self._create_response(request, tags)

    def get_object_tags(self, request, **kwargs):
        ctype = None
        try:
            ctype = ContentType.objects.get_by_natural_key(kwargs['app_label'], kwargs['object_type'])
        except ContentType.DoesNotExist:
            pass

        tags_ids = TaggedItem.objects.filter(object_id=kwargs['object_id']).filter(content_type=ctype).values_list('tag', flat=True)
        tags = Tag.objects.filter(id__in=tags_ids)
        return self._create_response(request, tags)

