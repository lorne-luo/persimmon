#coding=utf-8

from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib import admin
from transaction.models import *
from member.models import Bank, Enterprise
from django.forms import ModelForm
from django import forms
from django.db.models import Q
from django.utils.safestring import mark_safe


class TransactionMetaOperationForm(forms.ModelForm):
    class Meta:
        model = TransactionMetaOperation
        fields = '__all__'


class TransactionMetaOperationAddInline(admin.TabularInline):
    model = TransactionMetaOperation
    extra = 1
    can_delete = True
    exclude = ['sequence', ]
    verbose_name = u'贴现流程模板'
    verbose_name_plural = u'贴现流程设置'
    form = TransactionMetaOperationForm


class TransactionMetaOperationChangeInline(admin.TabularInline):
    model = TransactionMetaOperation
    extra = 0
    can_delete = True
    exclude = []
    verbose_name = u'贴现流程模板'
    verbose_name_plural = u'贴现流程设置'


class TicketFormerHolderAddInline(admin.TabularInline):
    model = TicketFormerHolder
    extra = 0
    can_delete = True
    exclude = ['transaction', ]
    verbose_name = u'历史持票人'
    verbose_name_plural = u'历史持票信息'


class TicketFormerHolderReadonlyInline(admin.TabularInline):
    model = TicketFormerHolder
    extra = 0
    max_num = 0
    can_delete = False
    exclude = ['claim', ]
    readonly_fields = ['name', ]
    verbose_name = u'历史持票人'
    verbose_name_plural = u'历史持票信息'


class TransactionOperationEditInline(admin.TabularInline):
    model = TransactionOperation
    extra = 0
    can_delete = False
    # exclude = ['sequence', 'description']
    # readonly_fields = ['operator_member', 'status', 'operation_type', 'operator_user', 'confirm_service', 'available_time', 'finish_time']
    verbose_name = u'贴现操作'
    verbose_name_plural = u'贴现操作流程'


class TransactionOperationReadonlyInline(admin.TabularInline):
    model = TransactionOperation
    extra = 0
    can_delete = False
    exclude = ['sequence', 'description']
    readonly_fields = ['operator_member', 'operator_user', 'operation_type', 'file_name', 'need_upload', 'status', 'upload_file', 'need_ems', 'ems_number', 'need_confirm',
                       'confirm_service', 'remark', 'available_time', 'finish_time']
    verbose_name = u'贴现操作'
    verbose_name_plural = u'贴现操作流程'


class TransactionOperationInline(admin.TabularInline):
    model = TransactionOperation
    extra = 0
    can_delete = False
    exclude = ['sequence', 'description']
    readonly_fields = ['operator_member', 'status', 'operation_type', 'operator_user', 'confirm_service', 'available_time', 'finish_time']
    verbose_name = u'贴现操作'
    verbose_name_plural = u'贴现操作流程'


from django.forms.models import BaseInlineFormSet


class TransactionOrderConfirmInlineFormset(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(TransactionOrderConfirmInlineFormset, self).__init__(*args, **kwargs)
        # self.obj_id = 1

    # 为了传参TransactionClaim的id给TransactionOrder Inline，特意重载
    @property
    def empty_form(self):
        form = self.form(
            auto_id=self.auto_id,
            prefix=self.add_prefix('__prefix__'),
            empty_permitted=True,
            receivable_enterprise_id=self.instance.receivable_enterprise.id,
        )
        self.add_fields(form, None)
        return form

    # 为了传参TransactionClaim的id给TransactionOrder Inline，特意重载
    def _construct_form(self, i, **kwargs):
        """
        Instantiates and returns the i-th form instance in a formset.
        """
        defaults = {
            'auto_id': self.auto_id,
            'prefix': self.add_prefix(i),
            'error_class': self.error_class,
            'receivable_enterprise_id': self.instance.receivable_enterprise.id,
        }
        if self.is_bound:
            defaults['data'] = self.data
            defaults['files'] = self.files
        if self.initial and 'initial' not in kwargs:
            try:
                defaults['initial'] = self.initial[i]
            except IndexError:
                pass
        # Allow extra forms to be empty, unless they're part of
        # the minimum forms.
        if i >= self.initial_form_count() and i >= self.min_num:
            defaults['empty_permitted'] = True
        defaults.update(kwargs)
        form = self.form(**defaults)
        self.add_fields(form, i)
        return form


class TransactionOrderConfirmForm(forms.ModelForm):
    hint = forms.CharField(label=_(u'收款企业业绩'), required=False, widget=forms.TextInput(attrs={'style': 'display:none;'}))
    transaction_sum = forms.CharField(label=_(u"年度贴现总额"), widget=forms.TextInput(attrs={'readonly': 'readonly', 'style': 'border:0'}))
    reference_count = forms.CharField(label=_(u"成功推荐会员数"), widget=forms.TextInput(attrs={'readonly': 'readonly', 'style': 'border:0'}))

    class Meta:
        model = TransactionOrder
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        receivable_enterprise_id = None
        if 'receivable_enterprise_id' in kwargs:
            receivable_enterprise_id = kwargs.pop('receivable_enterprise_id')

        super(TransactionOrderConfirmForm, self).__init__(*args, **kwargs)
        if not receivable_enterprise_id is None:
            payee_queryset = Enterprise.objects.filter(pk=receivable_enterprise_id)
            self.fields['receivable_enterprise'].queryset = payee_queryset
            self.fields['receivable_enterprise'].widget.attrs.update({'disabled': 'true'})
            self.fields['receivable_enterprise'].empty_label = None
            self.fields['receivable_enterprise'].empty_value = []
            # 付款企业的可选项去掉收款企业，不能自己付自己收
            self.fields['pay_enterprise'].queryset = Enterprise.objects.filter(~Q(id=receivable_enterprise_id))  # .all().exclude(pk=receivable_enterprise_id)
            # total transaction sum of payee
            order_list = TransactionOrder.objects.filter(receivable_enterprise_id=receivable_enterprise_id, status=TRANSACTION_DONE)
            sum = 0
            for order in order_list:
                sum += order.amount
            self.fields['transaction_sum'].initial = str(sum) + u' 元'
            if payee_queryset.count():
                self.fields['reference_count'].initial = str(payee_queryset[0].reference_count) + u' 个'
            else:
                self.fields['reference_count'].initial = u'0 个'
                # todo compute service fee automatically
                #self.fields['fee'].initial =
                #self.fields['fee'].widget.attrs.update({'readonly': 'readonly', 'style': 'border:0'})


class TransactionOrderConfirmInline(admin.StackedInline):
    model = TransactionOrder
    extra = 1
    can_delete = False
    max_num = 1
    exclude = ['ticket_number', 'amount', 'status', 'finish_time', 'invoice_status', 'ticket_status']
    verbose_name = u'贴现服务订单基本信息'
    verbose_name_plural = u'填写以下贴现服务订单信息'
    form = TransactionOrderConfirmForm
    formset = TransactionOrderConfirmInlineFormset


    def __init__(self, *args, **kwargs):
        super(TransactionOrderConfirmInline, self).__init__(*args, **kwargs)
        pass
        # self.fields['fee'].widget.attrs.update({'style': 'display:none;'})

        # def get_formset(self, request, obj=None, **kwargs):
        #     # Hack! Hook parent obj just in time to use in formfield_for_manytomany
        #     self.parent_obj = obj
        #     return super(TransactionOrderConfirmInline, self).get_formset(request, obj, **kwargs)

        # def save_model(self, request, obj, form, change):
        #
        #     obj.save()

        # def queryset(self, request):
        #     """Alter the queryset to return no existing entries"""
        #     # get the existing query set, then empty it.
        #     qs = super(TransactionOrderConfirmInline, self).queryset(request)
        #     return qs.none()


class TransactionClaimAddForm(forms.ModelForm):
    class Meta:
        model = TransactionClaim
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(TransactionClaimAddForm, self).__init__(*args, **kwargs)

        # for add
        if ('initial' in kwargs and
            kwargs['initial'] and
            'enterprise_id' in kwargs['initial']):

            self.fields['receivable_enterprise'].queryset = \
                Enterprise.objects.filter(pk=kwargs['initial']['enterprise_id'])
            self.fields['receivable_enterprise'].widget.attrs.update({'disabled': 'true'})
            self.fields['receivable_enterprise'].empty_label = None
            self.fields['receivable_enterprise'].empty_value = []
        # for change
        else:
            self.fields['receivable_enterprise'].queryset = \
                Enterprise.objects.filter(pk=kwargs['instance'].receivable_enterprise_id)
            self.fields['receivable_enterprise'].widget.attrs.update({'disabled': 'true'})
            self.fields['receivable_enterprise'].empty_label = None
            self.fields['receivable_enterprise'].empty_value = []


class TransactionClaimConfirmForm(forms.ModelForm):
    class Meta:
        model = TransactionClaim
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(TransactionClaimConfirmForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance']:
            self.fields['receivable_enterprise'].choices = [(kwargs['instance'].receivable_enterprise.id, kwargs['instance'].receivable_enterprise.name)]


# class TransactionOrderForm(forms.ModelForm):
#     hint = forms.CharField(label=_(u'收款企业业绩'), required=False, widget=forms.TextInput(attrs={'style': 'display:none;'}))
#     invoice_status = forms.CharField(label=_(u"发票状态"), widget=forms.TextInput(attrs={'readonly': 'readonly', 'style': 'border:0'}))
#     ticket_status = forms.CharField(label=_(u"汇票状态"), widget=forms.TextInput(attrs={'readonly': 'readonly', 'style': 'border:0'}))
#
#     class Meta:
#         model = TransactionOrder
#         fields = '__all__'






