from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from .models import AffiliateProduct, ProductClick
from .serializers import AffiliateProductListSerializer, AffiliateProductDetailSerializer


# ------------------------------------------------------------------ #
# Pagination
# ------------------------------------------------------------------ #

class NewsfeedPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'message': 'Products retrieved successfully',
            'data': {
                'count':    self.page.paginator.count,
                'next':     self.get_next_link(),
                'previous': self.get_previous_link(),
                'results':  data,
            }
        }, status=status.HTTP_200_OK)


# ------------------------------------------------------------------ #
# Newsfeed — main product list
# ------------------------------------------------------------------ #

class AffiliateProductNewsfeedView(generics.ListAPIView):
    """
    GET /api/affiliate/products/

    Returns paginated affiliate products for the home newsfeed.

    Query params:
        search      — full-text search across name, brand, description
        brand       — exact brand filter (case-insensitive)
        category    — partial category match
        colour      — colour filter
        min_price   — minimum price
        max_price   — maximum price
        ordering    — price_asc | price_desc | newest | discount
        page        — page number
        page_size   — results per page (default 20, max 100)
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = AffiliateProductListSerializer
    pagination_class = NewsfeedPagination

    def get_queryset(self):
        qs = AffiliateProduct.objects.filter(is_active=True)

        search    = self.request.query_params.get('search')
        brand     = self.request.query_params.get('brand')
        category  = self.request.query_params.get('category')
        colour    = self.request.query_params.get('colour')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        ordering  = self.request.query_params.get('ordering')

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(brand__icontains=search) |
                Q(description__icontains=search)
            )

        if brand:
            qs = qs.filter(brand__iexact=brand)

        if category:
            qs = qs.filter(category__icontains=category)

        if colour:
            qs = qs.filter(colour__icontains=colour)

        if min_price:
            try:
                qs = qs.filter(price__gte=float(min_price))
            except ValueError:
                pass

        if max_price:
            try:
                qs = qs.filter(price__lte=float(max_price))
            except ValueError:
                pass

        order_map = {
            'price_asc':  'price',
            'price_desc': '-price',
            'newest':     '-created_at',
            'discount':   'price',   # cheapest first as proxy for best deal
        }
        qs = qs.order_by(order_map.get(ordering, '-created_at'))

        return qs


# ------------------------------------------------------------------ #
# Product detail
# ------------------------------------------------------------------ #

class AffiliateProductDetailView(generics.RetrieveAPIView):
    """
    GET /api/affiliate/products/<id>/

    Returns full product details including the affiliate tracking link.
    The mobile app should open aw_deep_link in an in-app browser when
    the user taps 'Buy'.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = AffiliateProductDetailSerializer
    queryset = AffiliateProduct.objects.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'message': 'Product retrieved successfully',
            'data': serializer.data,
        }, status=status.HTTP_200_OK)


# ------------------------------------------------------------------ #
# Click tracking  (called before opening the affiliate link)
# ------------------------------------------------------------------ #

class ProductClickView(APIView):
    """
    POST /api/affiliate/products/<id>/click/

    Records a click for internal analytics, then returns the Awin
    affiliate tracking URL for the mobile app to open.

    The app flow is:
        1. User taps 'Buy'
        2. App calls POST /api/affiliate/products/<id>/click/
        3. Backend records the click and returns { affiliate_url }
        4. App opens affiliate_url in WebView / system browser
        5. User completes purchase on brand website
        6. Awin records conversion → MyClosly earns commission

    Authentication is optional — works for both logged-in and guest users.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, pk):
        try:
            product = AffiliateProduct.objects.get(pk=pk, is_active=True)
        except AffiliateProduct.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Record click — user may or may not be authenticated
        user = request.user if request.user.is_authenticated else None
        ProductClick.objects.create(product=product, user=user)

        return Response({
            'success': True,
            'message': 'Click recorded. Redirect user to affiliate_url.',
            'data': {
                'affiliate_url': product.aw_deep_link,
                'product_name':  product.name,
                'brand':         product.brand,
            }
        }, status=status.HTTP_200_OK)


# ------------------------------------------------------------------ #
# Brands list
# ------------------------------------------------------------------ #

class AffiliateBrandsListView(APIView):
    """
    GET /api/affiliate/brands/

    Returns all unique brands with product counts.
    Use this to populate the brand filter on the app.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        brands = (
            AffiliateProduct.objects
            .filter(is_active=True)
            .values('brand')
            .annotate(product_count=Count('id'))
            .order_by('brand')
        )
        return Response({
            'success': True,
            'message': 'Brands retrieved successfully',
            'data': {
                'brands': list(brands)
            }
        }, status=status.HTTP_200_OK)


# ------------------------------------------------------------------ #
# Categories list
# ------------------------------------------------------------------ #

class AffiliateCategoriesListView(APIView):
    """
    GET /api/affiliate/categories/

    Returns all unique categories with product counts.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        categories = (
            AffiliateProduct.objects
            .filter(is_active=True)
            .exclude(category='')
            .values('category')
            .annotate(product_count=Count('id'))
            .order_by('category')
        )
        return Response({
            'success': True,
            'message': 'Categories retrieved successfully',
            'data': {
                'categories': list(categories)
            }
        }, status=status.HTTP_200_OK)
