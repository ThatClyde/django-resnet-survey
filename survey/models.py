from django.db import models
from django.utils.timezone import now
from datetime import datetime


class Survey(models.Model):
    """
    Survey model has a set of questions.
    """
    title = models.CharField(max_length=1024)
    slug = models.SlugField(max_length=1024, primary_key=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    description = models.CharField(max_length=1024, null=False, blank=True)

    @models.permalink
    def get_absolute_url(self):
        return ('survey', (), {'slug': self.slug})

    @property
    def is_active(self):
        end_date = self.end_date
        if self.start_date:
            return self.start_date <= now() and (not end_date or now() <= end_date)
        return False

    @property
    def closed(self):
        return self.end_date <= now()

    def publish(self, dt=None):
        if dt is None:
            dt = now()
        self.start_date = dt
        self.save()

    def close(self, dt=None):
        if dt is None:
            dt = now()
        self.end_date = dt
        self.save()

    def set_future_date(self, field, dtStr):
        dt = datetime.strptime(dtStr, '%m/%d/%Y %I:%M %p')
        setattr(self, field, dt)
        self.save()

    def __unicode__(self):
        return self.title

    @property
    def cookie(self):
        """
            returns a cookie friendly name
        """
        return str(self.slug.replace('-', '') + 'ballotcookie')


class QuestionGroup(models.Model):
    """
    A QuestionGroup is a way to keep track of Questions associated with each other (mostly just used for Likert scales).
    """
    message = models.CharField(max_length=1024, blank=True)

    def __unicode__(self):
        return self.message


class Question(models.Model):
    """
    A Question is associated with a Survey and its type can be: textbox, textarea, checkbox, radio, or dropdown.
    """
    survey = models.ForeignKey('Survey')
    message = models.CharField(max_length=1024)
    group = models.ForeignKey('QuestionGroup', null=True, blank=True)
    required = models.BooleanField(default=False)

    QUESTION_TYPES = (
        ('TB', 'textbox'),
        ('TA', 'textarea'),
        ('CH', 'checkbox'),
        ('RA', 'radio'),
        ('DD', 'dropdown'),
    )
    type = models.CharField(max_length=2, choices=QUESTION_TYPES)

    def answer_with_text(self, text, ballot):
        if text:
            choice = self.choice_set.all()[0]
            Answer.objects.create(choice=choice, text=text, ballot=ballot)

    def answer_with_choices(self, choices, ballot):
        for choice in choices:
            Answer.objects.create(choice=choice, text=unicode(choice.pk), ballot=ballot)

    @classmethod
    def add_questions(cls, questions, survey):
        """
        Accepts a list of dictionaries containing question data.
        """
        for question_data in questions:
            question = cls.objects.create(survey=survey, message=question_data.get('message', ''), type=question_data.get('type', ''), required=question_data.get('required'))
            for choice_message in question_data.get('choices', []):
                Choice.objects.create(question=question, message=choice_message)
            if 'choices' not in question_data:
                Choice.objects.create(question=question, message='choice')

    def __unicode__(self):
        required_str = ""
        if self.required:
            required_str = "*"
        return required_str + self.message


class Choice(models.Model):
    """
    A Choice is an answer that can be picked as part of a question.
    """
    question = models.ForeignKey('Question')
    message = models.CharField(max_length=1024)

    def __unicode__(self):
        return self.message


class Answer(models.Model):
    """
    Answer contains the choice that the user has picked as their answer.
    """
    choice = models.ForeignKey('Choice')
    text = models.CharField(max_length=1024)
    ballot = models.ForeignKey('Ballot', null=True)

    def __unicode__(self):
        return self.text


class Ballot(models.Model):
    """
    Holds a set of Answers so they may be grouped.
    """
    ip = models.GenericIPAddressField(default='127.0.0.1')
    datetime = models.DateTimeField(default=now)
    survey = models.ForeignKey('Survey', null=True)

    def question_list(self):
        """
        Returns a list of question tuples and their associated choices and ballot answers (if any)
        """
        question_list = []
        for question in self.survey.question_set.all():
            choice_list = []
            for choice in question.choice_set.all():
                try:
                    answer = choice.answer_set.get(ballot=self)
                except Answer.DoesNotExist:
                    answer = None
                choice_list.append((choice, answer))
            question_tuple = (question, choice_list)
            question_list.append(question_tuple)
        return question_list
