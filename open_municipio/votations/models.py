from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.managers import QueryManager

from open_municipio.people.models import Group, InstitutionCharge, Sitting, Institution
from open_municipio.acts.models import Act


class Votation(models.Model):
    """
    WRITEME
    """
    OUTCOMES = Choices(
        (0, 'No Esito'),
        (1, 'Approvato'),
        (2, 'Respinto'),
        (3, 'SI Numero Legale'),
        (4, 'NO Numero Legale'),
        (5, 'Annullata'),
    )

    idnum = models.CharField(blank=True, max_length=64)
    sitting = models.ForeignKey(Sitting, null=True)
    act = models.ForeignKey(Act, null=True)
    
    # this field is used to keep the textual description of the related act
    # as expressed in the voting system
    act_descr = models.CharField(blank=True, max_length=255)
    
    group_set = models.ManyToManyField(Group, through='GroupVote')
    charge_set = models.ManyToManyField(InstitutionCharge, through='ChargeVote')
    n_legal = models.IntegerField(default=0)
    n_presents = models.IntegerField(default=0)
    n_partecipants = models.IntegerField(default=0)
    n_absents = models.IntegerField(default=0)
    n_yes = models.IntegerField(default=0)
    n_no = models.IntegerField(default=0)
    n_abst = models.IntegerField(default=0)
    n_maj = models.IntegerField(default=0)
    outcome = models.IntegerField(choices=OUTCOMES, blank=True, null=True)
    is_key = models.BooleanField(default=False, help_text=_("Specify whether this is a key votation"))    
    n_rebels = models.IntegerField(default= 0)

    # default manager must be explicitly defined, when
    # at least another manager is present
    objects = models.Manager()

    # use this manager to retrieve only key votations
    key = QueryManager(is_key=True).order_by('-sitting__date')

    # use this manager to retrieve only linked acts
    is_linked_to_act = QueryManager(act__isnull=False)

    # activation of the ``is_linked_filter``
    # add ``act`` to the ``list_filter`` list in ``admin.py``
    # to filter votations based on the existence of a related act
    act.is_linked_filter = True

    @property
    def is_key_yesno(self):
        if self.is_key:
            return _('yes')
        else:
            return _('no')

    class Meta:
        verbose_name = _('votation')
        verbose_name_plural = _('votations')
    
    def __unicode__(self):
        return u'votation %s' % self.idnum

    @models.permalink
    def get_absolute_url(self):
        return 'om_votation_detail', [str(self.pk)]
    
    @property
    def group_votes(self):
        return self.groupvote_set.all()
    
    @property
    def charge_votes(self):
        return self.chargevote_set.all()

    @property
    def transitions(self):
        return self.transition_set.all()

    @property
    def is_linked(self):
        if self.act is None:
            return False
        else:
            return True

    @property
    def is_secret(self):
        for vote in self.charge_votes:
            return vote.vote == ChargeVote.VOTES.secret

    def update_presence_caches(self):
        """
        update presence caches for each voting charge of this votation
        """
        for vc in self.charge_votes:
            vc.charge.update_presence_cache()


class GroupVote(TimeStampedModel):
    """
    WRITEME
    """
    VOTES = Choices(
      ('YES', 'yes', _('Yes')),
      ('NO', 'no', _('No')),
      ('ABSTAINED', 'abstained', _('Abstained')),
      ('NON_COMPUTABLE', 'noncomputable', _('Non computable')),
    )
    
    votation = models.ForeignKey(Votation)
    vote = models.CharField(choices=VOTES, max_length=16)
    group = models.ForeignKey(Group)

    # cache fields
    n_presents = models.IntegerField(default=0)
    n_yes = models.IntegerField(default=0)
    n_no = models.IntegerField(default=0)
    n_abst = models.IntegerField(default=0)
    n_rebels = models.IntegerField(default=0)
    n_absents = models.IntegerField(default=0)

    class Meta:
        db_table = u'votations_group_vote'    
        verbose_name = _('group vote')
        verbose_name_plural = _('group votes')

    def __unicode__(self):
        return u"%s - %s - %s" % (self.votation, self.group.acronym, self.get_vote_display())


class ChargeVote(TimeStampedModel):
    """
    WRITEME
    """  
    VOTES = Choices(
        ('YES', 'yes', _('Yes')),
        ('NO', 'no', _('No')),
        ('ABSTAINED', 'abstained', _('Abstained')),
        ('CANCELED', 'canceled', _('Vote was canceled')),
        ('PRES', 'pres', _('Present but not voting')),
        ('SECRET', 'secret', _('Secret votation')),
        ('ABSENT', 'absent', _('Is absent')),
        ('UNTRACKED', 'untracked', _('Vote was not tracked')),  # nothing can be said about presence
    )
    
    votation = models.ForeignKey(Votation)
    vote = models.CharField(choices=VOTES, max_length=12)
    charge = models.ForeignKey(InstitutionCharge)
    is_rebel = models.BooleanField(default=False)

    @property
    def original_charge(self):
        """
        Charge in committees are connected to an original Counselor charge.
        Using original_charge assures you always refer to the counselor InstitutionCharge
        """
        if self.charge.original_charge is not None:
            return self.charge.original_charge
        else:
            return self.charge

    @property
    def charge_group_at_vote_date(self):
        return self.original_charge.person.get_current_group(moment=self.votation.sitting.date.strftime('%Y-%m-%d'))
    
    class Meta:
        db_table = u'votations_charge_vote'    
        verbose_name = _('charge vote')
        verbose_name_plural = _('charge votes')

    def __unicode__(self):
        return u"%s - %s - %s" % (self.votation, self.original_charge.person, self.get_vote_display())