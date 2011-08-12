import commonware.log
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from jetpack.models import Package
from .helpers import package_search
from .forms import SearchForm

log = commonware.log.getLogger('f.search')


def search(request):
    form = SearchForm(request.GET)
    form.is_valid()
    query = form.cleaned_data
    q = query.get('q')
    type_ = query.get('type') or None
    types = {'a': 'addon', 'l': 'library'}
    page = query.get('page') or 1


    filters = {}
    filters['user'] = request.user

    author = query.get('author')
    if author:
        filters['author'] = author.id
    if query.get('copies'):
        filters['copies_count__gte'] = query['copies']


    results = {}
    facets = {}
    if type_:
        filters['type'] = type_
        qs = package_search(q, **filters).facet(copies={'terms':
            {'field':'copies_count'}})
        results['pager'] = Paginator(qs, per_page=20).page(page)
        facets = _facets(results['pager'].object_list.facets)
        facets['everyone_total'] = len(qs)
        template = 'results.html'
    else:
        # combined view
        results['addons'] = package_search(q, type='a', **filters).facet(
                copies={'terms':{'field':'copies_count'}})[:5]
        results['libraries'] = package_search(q, type='l', **filters)[:5]
        facets = _facets(results['addons'].facets)
        facets['everyone_total'] = facets['combined_total']
        template = 'aggregate.html'



    ctx = {
        'q': q,
        'page': 'search',
        'form': form,
        'query': query,
        'type': types.get(type_, None)
    }
    ctx.update(results)
    ctx.update(facets)

    if request.is_ajax():
        template = 'ajax/' + template
    return _render(request, template, ctx)


def rss_redirect(request, type_):
    from base.helpers import urlparams
    form = SearchForm(request.GET)
    form.is_valid()

    query = dict(form.cleaned_data)
    if type_ != 'combined':
        query['type'] = type_[0]

    return redirect(urlparams(reverse('search.rss'), **query), permanent=True)


def _render(request, template, data={}):
    return render_to_response(template, data, RequestContext(request))


def _facets(facets):
    type_totals = dict((t['term'], t['count']) for t in facets['types'])
    my_total = 0
    if 'author' in facets and len(facets['author']):
        my_total = facets['author'][0]['count']

    copies_steps = []
    if 'copies' in facets:
        copies_steps = [t['term'] for t in facets['copies']]
        if len(copies_steps) > 1 or not copies_steps.count(0):
            if not copies_steps.count(0):
                copies_steps.append(0)
            copies_steps.sort()
        else:
            copies_steps = []

    return {
        'addon_total': type_totals.get('a', 0),
        'library_total': type_totals.get('l', 0),
        'my_total': my_total,
        'combined_total': type_totals.get('a', 0) + type_totals.get('l', 0),
        'copies_steps': copies_steps,
    }
