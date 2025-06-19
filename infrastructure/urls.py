from django.urls import path
from .views import (
    home, report_issue, my_issues, issue_detail,
    ajax_load_floors, ajax_load_rooms, ajax_load_equipment, ajax_load_equipment_by_block, 
    ajax_load_equipment_by_floor, ajax_load_equipment_details, ajax_get_equipment_count
)

urlpatterns = [
    path('', home, name='home'),
    path('report/', report_issue, name='report_issue'),
    path('my-issues/', my_issues, name='my_issues'),
    path('my-issues/<int:pk>/', issue_detail, name='issue_detail'),
    path('ajax/load-floors/', ajax_load_floors, name='ajax_load_floors'),
    path('ajax/load-rooms/', ajax_load_rooms, name='ajax_load_rooms'),
    path('ajax/load-equipment/', ajax_load_equipment, name='ajax_load_equipment'),
    path('ajax/load-equipment-by-block/', ajax_load_equipment_by_block, name='ajax_load_equipment_by_block'),
    path('ajax/load-equipment-by-floor/', ajax_load_equipment_by_floor, name='ajax_load_equipment_by_floor'),
    path('ajax/load-equipment-details/',ajax_load_equipment_details, name='ajax_load_equipment_details'),
    path('ajax/get-equipment-count/', ajax_get_equipment_count, name='ajax_get_equipment_count'),
]