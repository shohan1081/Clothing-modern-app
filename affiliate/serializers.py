from rest_framework import serializers
from .models import AffiliateProduct


class AffiliateProductListSerializer(serializers.ModelSerializer):
    """
    Compact serializer for the newsfeed list view.
    Omits heavy fields like full description to keep responses fast.
    """
    discount_percent = serializers.ReadOnlyField()

    class Meta:
        model = AffiliateProduct
        fields = [
            'id',
            'aw_product_id',
            'name',
            'brand',
            'category',
            'price',
            'rrp_price',
            'discount_percent',
            'currency',
            'colour',
            'image_url',
            'advertiser_name',
            'is_active',
            'created_at',
        ]
        read_only_fields = fields


class AffiliateProductDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for the product detail view.
    Includes description and the affiliate tracking link.
    """
    discount_percent = serializers.ReadOnlyField()

    class Meta:
        model = AffiliateProduct
        fields = [
            'id',
            'aw_product_id',
            'name',
            'brand',
            'category',
            'description',
            'price',
            'rrp_price',
            'discount_percent',
            'currency',
            'colour',
            'image_url',
            'aw_deep_link',          # affiliate tracking URL for 'Buy' button
            'merchant_deep_link',    # direct brand URL (fallback)
            'advertiser_name',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
