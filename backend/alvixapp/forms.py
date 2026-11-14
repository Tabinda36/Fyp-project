from django import forms
from .models import Report, StudentAssessment, AdminCourse, UserSettings, Profile, AvatarSettings


# ==========================================
# 1. REPORTS FORM
# ==========================================
class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = [
            "course_name",
            "problem_type",
            "problem_title",
            "problem_description",
        ]

        widgets = {
            "course_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter Course Name"
            }),
            "problem_type": forms.Select(attrs={
                "class": "form-select"
            }),
            "problem_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Problem Title"
            }),
            "problem_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Explain your problem in detail..."
            }),
        }


# ==========================================
# 2. MANDATORY STUDENT ASSESSMENT FORM
# ==========================================
INTEREST_AREA_CHOICES = [
    ('', '-- Select Your Interest Area --'),
    ('Creativity', 'Creativity'),
    ('Development', 'Development'),
    ('Designing', 'Designing'),
    ('Marketing', 'Marketing'),
]

GOAL_CHOICES = [
    ('', '-- Select Your Goal --'),
    ('Practical', 'Practical'),
    ('Theory', 'Theory'),
    ('Mixed', 'Mixed'),
]

class StudentProfileAssessmentForm(forms.Form):
    interest_area = forms.ChoiceField(
        choices=INTEREST_AREA_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'interest_area_select'}),
        label="Interest area"
    )
    goal = forms.ChoiceField(
        choices=GOAL_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'goal_select'}),
        label="Goal"
    )
    expectations = forms.CharField(
        required=True,
        min_length=20,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'id': 'expectations_input',
            'rows': 4,
            'placeholder': 'What do you actually want to learn from this course, and what do you expect to be able to do after it?'
        }),
        label="What do you actually want to learn from this course, and what do you expect to be able to do after it?",
        error_messages={
            'min_length': 'Your expectations must be at least 20 characters long.',
            'required': 'Please describe what you want to learn and expect to do after this course.'
        }
    )

    def clean_expectations(self):
        expectations = self.cleaned_data.get('expectations', '').strip()
        if len(expectations) < 20:
            raise forms.ValidationError('Your expectations must be at least 20 characters long.')
        return expectations


# ==========================================
# 3. LEGACY / EXTENDED STUDENT ASSESSMENT FORM
# ==========================================
INTEREST_CHOICES = [
    ('', '-- Select Your Interest --'),
    ('creativity_visuals', 'Creativity & Visual Arts'),
    ('logic_problem_solving', 'Logic & Problem Solving'),
    ('structuring_building', 'Structuring & Building Things'),
    ('innovation_future_tech', 'Innovation & Exploring New Ideas'),
    ('management_strategy', 'Management, Strategy & Planning'),
    ('research_analysis', 'Research, Analysis & Information Gathering'),
]

class StudentAssessmentForm(forms.ModelForm):
    class Meta:
        model = StudentAssessment
        fields = '__all__'
        exclude = ['created_at', 'selected_course', 'interest']

        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter your age'}),
            'education_level': forms.Select(attrs={'class': 'form-select'}),
            'knowledge_level': forms.Select(attrs={'class': 'form-select'}),
            'learning_goal': forms.Select(attrs={'class': 'form-select'}),
            'learning_style': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interest'] = forms.ChoiceField(
            choices=INTEREST_CHOICES,
            widget=forms.Select(attrs={'class': 'form-select'}),
            required=True
        )


# ==========================================
# 4. SETTINGS FORM
# ==========================================
class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['theme', 'email_notifications', 'ai_notifications', 'public_profile']


# ==========================================
# 5. AVATAR & AI TEACHER SETTINGS FORM
# ==========================================
class AvatarSettingsForm(forms.ModelForm):
    class Meta:
        model = AvatarSettings
        fields = [
            'avatar_name',
            'developer_name',
            'university_or_department',
            'avatar_name_pronunciation',
            'play_full_intro_every_day',
        ]
        widgets = {
            'avatar_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Inara'
            }),
            'developer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Tabinda Rukhsar'
            }),
            'university_or_department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Department of Computer Science (optional)'
            }),
            'avatar_name_pronunciation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. ee-nah-rah (used only for speech)'
            }),
            'play_full_intro_every_day': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
