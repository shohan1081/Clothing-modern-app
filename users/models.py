from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .managers import UserManager
import uuid
from django.contrib.auth.hashers import make_password, check_password


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model
    Uses email as the unique identifier instead of username
    """
    
    # Primary identifier (UUID for better security)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for the user")
    )
    
    # Required fields
    email = models.EmailField(
        _('email address'),
        unique=True,
        max_length=255,
        db_index=True,
        help_text=_("User's email address (used for login)")
    )
    
    name = models.CharField(
        _('full name'),
        max_length=150,
        help_text=_("User's full name")
    )
    
    date_of_birth = models.DateField(
        _('date of birth'),
        null=True,
        blank=True,
        help_text=_("User's date of birth")
    )
   
    gender = models.CharField(
        _('gender'),
        max_length=20,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say'),
        ],
        null=True,
        blank=True,
        help_text=_("User's gender")
    )

    occupation = models.CharField(
        _('occupation'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("User's occupation")
    )

    country = models.CharField(
        _('country'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("User's country")
    )
    
    # Status fields
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_("Designates whether this user should be treated as active.")
    )
    
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_("Designates whether the user can log into admin site.")
    )
    
    is_email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_("Designates whether user's email has been verified")
    )

    is_subscribed = models.BooleanField(
        _('subscribed'),
        default=False,
        help_text=_("Designates whether the user has an active subscription")
    )
    
    # Firebase integration
    firebase_uid = models.CharField(
        _('firebase uid'),
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Firebase UID for social login integration")
    )
    
    # Authentication provider tracking
    auth_provider = models.CharField(
        _('authentication provider'),
        max_length=50,
        default='email',
        choices=[
            ('email', 'Email/Password'),
            ('google', 'Google'),
            ('apple', 'Apple'),
        ],
        help_text=_("Primary authentication method used by user")
    )
    
    # Profile picture
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        help_text=_("User's profile picture")
    )

    bio = models.TextField(
        _('bio'),
        null=True,
        blank=True,
        help_text=_("User's bio")
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        _('date joined'),
        default=timezone.now,
        help_text=_("Date when user registered")
    )
    
    last_login = models.DateTimeField(
        _('last login'),
        null=True,
        blank=True,
        help_text=_("Date of user's last login")
    )
    
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_("Last time user data was updated")
    )
    
    # OTP fields
    otp = models.CharField(max_length=4, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    # journal_pin = models.CharField(max_length=128, null=True, blank=True)

    preferred_language = models.CharField(
        max_length=10,
        choices=[('en', 'English'), ('hi', 'Hindi'), ('pt', 'Portuguese')],
        default='en',
        help_text=_("User's preferred language for API responses")
    )

    # Set email as the unique identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']  # Required when creating superuser
    
    # Use custom manager
    objects = UserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['firebase_uid']),
            models.Index(fields=['is_active', 'is_email_verified']),
        ]
    
    def __str__(self):
        """String representation of user"""
        return self.email
    
    def get_full_name(self):
        """Return user's full name"""
        return self.name
    
    def get_short_name(self):
        """Return user's first name"""
        return self.name.split()[0] if self.name else self.email

    def is_otp_valid(self, expiry_minutes=10):
        """
        Check if OTP is still valid
        
        Args:
            expiry_minutes (int): Number of minutes before OTP expires
            
        Returns:
            bool: True if OTP is valid, False otherwise
        """
        if not self.otp_created_at:
            return False
        
        expiry_time = self.otp_created_at + timezone.timedelta(minutes=expiry_minutes)
        return timezone.now() < expiry_time

    def clear_otp(self):
        """Clear OTP after successful verification"""
        self.otp = None
        self.otp_created_at = None
        self.save(update_fields=['otp', 'otp_created_at'])



class UserPreference(models.Model):
    """
    Stores all onboarding preference data collected across 4 screens.

    Page 1 (1341-456) — Style Identity:
        style_goals, style_vibe, fashion_openness

    Page 2 (9-2427) — Lifestyle & Fit:
        lifestyle_tags, body_type, fit_preference, height_cm, weight_kg

    Page 3 (87-1217) — Wardrobe Details:
        skin_tone, color_palette, clothing_categories, preferred_brands

    Page 4 (1197-1717) — Budget & Shopping:
        budget_range, shopping_frequency, sustainability_preference

    All fields are optional (blank=True, null=True / default=[]).
    The user can skip any page or any field — no validation errors.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences',
        verbose_name=_('user'),
    )

    # ------------------------------------------------------------------ #
    # PAGE 1 — Style Identity / Onboarding intro
    # ------------------------------------------------------------------ #

    STYLE_GOAL_CHOICES = [
        ('refresh_wardrobe',    'Refresh my wardrobe'),
        ('find_my_style',       'Find my personal style'),
        ('dress_for_occasions', 'Dress for specific occasions'),
        ('shop_smarter',        'Shop smarter & sustainably'),
        ('explore_trends',      'Explore new trends'),
    ]
    style_goals = models.JSONField(
        _('style goals'),
        default=list, blank=True,
        help_text=_("List of style goal keys from STYLE_GOAL_CHOICES"),
    )

    VIBE_CHOICES = [
        ('classic',     'Classic & Timeless'),
        ('streetwear',  'Streetwear & Urban'),
        ('minimalist',  'Minimalist & Clean'),
        ('bohemian',    'Bohemian & Free-spirited'),
        ('romantic',    'Romantic & Feminine'),
        ('sporty',      'Sporty & Active'),
        ('edgy',        'Edgy & Bold'),
        ('preppy',      'Preppy & Smart'),
    ]
    style_vibe = models.JSONField(
        _('style vibe'),
        default=list, blank=True,
        help_text=_("List of vibe keys from VIBE_CHOICES"),
    )

    OPENNESS_CHOICES = [
        ('stick_to_classics', 'I stick to what I know'),
        ('sometimes_new',     'I try new things sometimes'),
        ('love_experimenting','I love experimenting'),
    ]
    fashion_openness = models.CharField(
        _('fashion openness'),
        max_length=30, blank=True, default='',
        choices=OPENNESS_CHOICES,
    )

    # ------------------------------------------------------------------ #
    # PAGE 2 — Lifestyle & Body Fit
    # ------------------------------------------------------------------ #

    LIFESTYLE_CHOICES = [
        ('work_office',     'Work / Office'),
        ('casual_everyday', 'Casual Everyday'),
        ('active_sport',    'Active / Sport'),
        ('going_out',       'Going Out / Nightlife'),
        ('travel',          'Travel'),
        ('formal_events',   'Formal / Events'),
        ('home_lounge',     'Home / Lounge'),
    ]
    lifestyle_tags = models.JSONField(
        _('lifestyle tags'),
        default=list, blank=True,
        help_text=_("List of lifestyle keys from LIFESTYLE_CHOICES"),
    )

    BODY_TYPE_CHOICES = [
        ('hourglass',    'Hourglass'),
        ('pear',         'Pear'),
        ('apple',        'Apple'),
        ('rectangle',    'Rectangle'),
        ('inverted_triangle', 'Inverted Triangle'),
        ('prefer_not',   'Prefer not to say'),
    ]
    body_type = models.CharField(
        _('body type'),
        max_length=25, blank=True, default='',
        choices=BODY_TYPE_CHOICES,
    )

    FIT_CHOICES = [
        ('slim',      'Slim / Fitted'),
        ('regular',   'Regular'),
        ('relaxed',   'Relaxed'),
        ('oversized', 'Oversized'),
    ]
    fit_preference = models.CharField(
        _('fit preference'),
        max_length=15, blank=True, default='',
        choices=FIT_CHOICES,
    )

    height_cm = models.PositiveSmallIntegerField(
        _('height (cm)'),
        null=True, blank=True,
    )

    weight_kg = models.PositiveSmallIntegerField(
        _('weight (kg)'),
        null=True, blank=True,
    )

    # ------------------------------------------------------------------ #
    # PAGE 3 — Wardrobe Details
    # ------------------------------------------------------------------ #

    # Skin tone — stored as hex color code, e.g. "#F1C27D"
    SKIN_TONE_CHOICES = [
        ('#FDDBB4', 'Fair / Porcelain'),
        ('#F5CBA7', 'Light'),
        ('#F0B27A', 'Light-Medium'),
        ('#E59866', 'Medium / Olive'),
        ('#CA6F1E', 'Medium-Dark'),
        ('#A04000', 'Dark'),
        ('#6E2C00', 'Deep / Ebony'),
    ]
    skin_tone = models.CharField(
        _('skin tone'),
        max_length=10, blank=True, default='',
        help_text=_("Hex color code representing skin tone, e.g. #F5CBA7"),
    )

    PALETTE_CHOICES = [
        ('neutral_minimalist', 'Neutral Minimalist'),
        ('bold_rich',          'Bold & Rich'),
        ('soft_romantic',      'Soft & Romantic'),
        ('earthy_warm',        'Earthy & Warm'),
    ]
    color_palette = models.CharField(
        _('color palette'),
        max_length=25, blank=True, default='',
        choices=PALETTE_CHOICES,
    )

    # Clothing categories — nested dict e.g.
    # {"tops": ["shirts","hoodies"], "bottoms": ["jeans"], ...}
    CLOTHING_CATEGORY_OPTIONS = {
        "tops":                 ["shirts", "t-shirts", "hoodies", "sweaters", "blouses", "cardigans"],
        "bottoms":              ["jeans", "trousers", "shorts", "skirts"],
        "dresses_outerwear":    ["blazers", "coats", "jackets", "dresses", "jumpsuits"],
        "active_lounge_swim":   ["activewear", "loungewear", "swimwear", "lingerie"],
        "shoes":                ["loafers", "sneakers", "boots", "heels", "sandals"],
        "bags_accessories":     ["backpacks", "wallets", "watches", "hats", "belts",
                                 "sunglasses", "handbags", "scarves", "jewellery"],
    }
    clothing_categories = models.JSONField(
        _('clothing categories'),
        default=dict, blank=True,
        help_text=_(
            'Dict of selected clothing categories. '
            'e.g. {"tops":["shirts","hoodies"],"shoes":["sneakers"]}'
        ),
    )

    # Preferred brands — stored as list of brand name strings
    BRAND_OPTIONS = {
        "popular":          ["zara", "uniqlo", "levi's", "nike", "cos", "arket"],
        "everyday":         ["zara", "h&m", "mango", "uniqlo", "gap", "levi's",
                             "nike", "adidas"],
        "designer_cult":    ["acne studios", "ralph lauren", "tommy hilfiger",
                             "reiss", "banana republic"],
    }
    preferred_brands = models.JSONField(
        _('preferred brands'),
        default=list, blank=True,
        help_text=_("List of brand name strings the user prefers"),
    )

    # ------------------------------------------------------------------ #
    # PAGE 4 — Budget & Shopping habits
    # ------------------------------------------------------------------ #

    BUDGET_CHOICES = [
        ('budget',    'Budget (under £30 per item)'),
        ('mid_range', 'Mid-range (£30–£100)'),
        ('premium',   'Premium (£100–£300)'),
        ('luxury',    'Luxury (£300+)'),
    ]
    budget_range = models.CharField(
        _('budget range'),
        max_length=15, blank=True, default='',
        choices=BUDGET_CHOICES,
    )

    FREQUENCY_CHOICES = [
        ('rarely',      'Rarely (few times a year)'),
        ('monthly',     'Monthly'),
        ('bi_weekly',   'Every two weeks'),
        ('weekly',      'Weekly'),
    ]
    shopping_frequency = models.CharField(
        _('shopping frequency'),
        max_length=15, blank=True, default='',
        choices=FREQUENCY_CHOICES,
    )

    SUSTAINABILITY_CHOICES = [
        ('not_important',       'Not important to me'),
        ('somewhat_important',  'Somewhat important'),
        ('very_important',      'Very important'),
        ('only_sustainable',    'I only buy sustainable'),
    ]
    sustainability_preference = models.CharField(
        _('sustainability preference'),
        max_length=20, blank=True, default='',
        choices=SUSTAINABILITY_CHOICES,
    )

    # ------------------------------------------------------------------ #
    # Meta
    # ------------------------------------------------------------------ #

    onboarding_completed = models.BooleanField(
        _('onboarding completed'),
        default=False,
        help_text=_("True once user has submitted at least one preference page"),
    )

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('user preference')
        verbose_name_plural = _('user preferences')

    def __str__(self):
        return f"Preferences — {self.user.email}"


class AccountDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Deletion request for {self.email}"

class ProfileDataDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile data deletion request for {self.email}"

class UserLoginHistory(models.Model):
    """
    Track user login history for security purposes
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        help_text=_("User who logged in")
    )
    
    login_time = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Time of login")
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address used for login")
    )
    
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text=_("Browser/device user agent string")
    )
    
    auth_method = models.CharField(
        max_length=50,
        default='email',
        help_text=_("Authentication method used")
    )
    
    class Meta:
        verbose_name = _('login history')
        verbose_name_plural = _('login histories')
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.login_time}"