from django.contrib import admin
from .models import (
    Block, Floor, Room, 
    EquipmentCategory, Equipment,
    Generator, MaintenanceRequest,
    MaintenanceLog
)
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Q, Avg
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from django.contrib.admin import AdminSite

# Custom Admin Site with Charts
class CustomAdminSite(AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', self.admin_view(self.analytics_view), name='analytics'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}        
        return super().index(request, extra_context)

    def analytics_view(self, request):
        # Generate all charts for the analytics page
        context = {
            'status_chart': self.generate_status_chart(),
            'priority_chart': self.generate_priority_chart(),
            'equipment_chart': self.generate_equipment_chart(),
            'block_chart': self.generate_block_chart(),
            'timeseries_chart': self.generate_timeseries_chart(),
            **self.each_context(request),
        }
        return render(request, 'admin/analytics.html', context)

    def generate_status_chart(self):
        status_data = (
            MaintenanceRequest.objects
            .values('status')
            .annotate(count=Count('status'))
            .order_by('-count')
        )
        
        df = pd.DataFrame(list(status_data))
        fig = px.pie(
            df, 
            values='count', 
            names='status', 
            title='Maintenance Requests by Status',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def generate_priority_chart(self):
        priority_data = (
            MaintenanceRequest.objects
            .values('priority')
            .annotate(count=Count('priority'))
            .order_by('priority')
        )
        
        df = pd.DataFrame(list(priority_data))
        priority_colors = {
            'LOW': '#36b9cc',
            'MED': '#1cc88a',
            'HIGH': '#f6c23e',
            'CRIT': '#e74a3b'
        }
        
        fig = px.bar(
            df,
            x='priority',
            y='count',
            title='Maintenance Requests by Priority',
            color='priority',
            color_discrete_map=priority_colors,
            text='count'
        )
        fig.update_layout(
            xaxis_title="Priority Level",
            yaxis_title="Number of Requests",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        fig.update_traces(
            textposition='outside',
            marker_line_color='rgb(8,48,107)',
            marker_line_width=1.5
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def generate_equipment_chart(self):
        equipment_data = (
            Equipment.objects
            .values('category__name', 'status')
            .annotate(count=Count('id'))
            .order_by('category__name', 'status')
        )
        
        df = pd.DataFrame(list(equipment_data))
        pivot_df = df.pivot(
            index='category__name',
            columns='status',
            values='count'
        ).fillna(0)
        
        fig = go.Figure()
        for status in pivot_df.columns:
            fig.add_trace(go.Bar(
                x=pivot_df.index,
                y=pivot_df[status],
                name=status,
                text=pivot_df[status],
                textposition='auto'
            ))
        
        fig.update_layout(
            barmode='stack',
            title='Equipment Status by Category',
            xaxis_title="Equipment Category",
            yaxis_title="Number of Items",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            )
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def generate_block_chart(self):
        block_data = (
            MaintenanceRequest.objects
            .values('block__code')
            .annotate(count=Count('id'))
            .order_by('block__code')
        )
        
        df = pd.DataFrame(list(block_data))
        fig = px.sunburst(
            df,
            path=['block__code'],
            values='count',
            title='Maintenance Requests by Block',
            color='count',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            margin=dict(t=40, l=0, r=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def generate_timeseries_chart(self):
        timeseries_data = (
            MaintenanceRequest.objects
            .extra(select={'day': "date(created_at)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        df = pd.DataFrame(list(timeseries_data))
        df['day'] = pd.to_datetime(df['day'])
        df['7day_avg'] = df['count'].rolling(window=7).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=df['count'],
            name='Daily Requests',
            mode='lines+markers',
            line=dict(color='#4e73df', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=df['7day_avg'],
            name='7-Day Average',
            mode='lines',
            line=dict(color='#1cc88a', width=3, dash='dot')
        ))
        
        fig.update_layout(
            title='Maintenance Requests Over Time',
            xaxis_title="Date",
            yaxis_title="Number of Requests",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

# Create custom admin site instance
custom_admin_site = CustomAdminSite(name='custom_admin')

# Inline Admin Classes (same as before)
class FloorInline(admin.TabularInline):
    model = Floor
    extra = 0
    fields = ['number', 'name']
    show_change_link = True

class RoomInline(admin.TabularInline):
    model = Room
    extra = 0
    fields = ['number', 'name', 'room_type']
    show_change_link = True
    readonly_fields = ['is_generator_room']

class EquipmentInline(admin.TabularInline):
    model = Equipment
    extra = 0
    fields = ['name', 'model_number', 'status']
    show_change_link = True

class MaintenanceLogInline(admin.TabularInline):
    model = MaintenanceLog
    extra = 0
    readonly_fields = ['completion_date']
    fields = ['technician', 'action_taken', 'completion_date']

# Register all models with the custom admin site
@admin.register(Block, site=custom_admin_site)
class BlockAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'has_multiple_floors', 'room_count']
    list_filter = ['has_multiple_floors']
    search_fields = ['code', 'name']
    inlines = [FloorInline, RoomInline]
    
    def room_count(self, obj):
        return obj.rooms.count()
    room_count.short_description = "Rooms"

@admin.register(Floor, site=custom_admin_site)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['block', 'number', 'name']
    list_filter = ['block']
    search_fields = ['block__code', 'number', 'name']
    ordering = ['block', 'number']

@admin.register(Room, site=custom_admin_site)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['block', 'floor_display', 'number', 'name', 'room_type', 'is_generator_room']
    list_filter = ['block', 'room_type', 'is_generator_room']
    search_fields = ['block__code', 'number', 'name']
    inlines = [EquipmentInline]
    
    def floor_display(self, obj):
        return obj.floor.number if obj.floor else "-"
    floor_display.short_description = "Floor"

@admin.register(EquipmentCategory, site=custom_admin_site)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'maintenance_interval', 'equipment_count']
    search_fields = ['name']
    
    def equipment_count(self, obj):
        return obj.equipment.count()
    equipment_count.short_description = "Equipment Count"

@admin.register(Equipment, site=custom_admin_site)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_location', 'category', 'status', 'last_maintenance']
    list_filter = ['category', 'status', 'room__block','block', 'floor']
    search_fields = ['name', 'model_number', 'serial_number']
    list_select_related = ['category', 'room', 'room__block', 'floor', 'floor__block', 'block']
   
    def room_location(self, obj):
        if obj.room:
            return f"{obj.room.block.code}{obj.room.number}"
        elif obj.floor:
            return f"Block {obj.floor.block.code} - Floor {obj.floor.number}"
        elif obj.block:
            return f"Block {obj.block.code}"
        return "No Location Assigned"
    room_location.short_description = "Location"
    room_location.admin_order_field = 'name'


@admin.register(Generator, site=custom_admin_site)
class GeneratorAdmin(admin.ModelAdmin):
    list_display = ['room_location', 'capacity_kva', 'fuel_type', 'next_service']
    list_filter = ['fuel_type']
    search_fields = ['room__block__code', 'room__number']
    
    def room_location(self, obj):
        return f"{obj.room.block.code}{obj.room.number}"
    room_location.short_description = "Location"

@admin.register(MaintenanceRequest, site=custom_admin_site)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = [
        'reported_by', 'short_problem', 'location', 
        'issue_type', 'priority', 'status', 
        'created_at', 'image'
    ]
    list_filter = ['status', 'priority', 'issue_type', 'block']
    search_fields = ['problem', 'description', 'room__number']
    list_select_related = ['block', 'floor', 'room', 'reported_by']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [MaintenanceLogInline]
    actions = ['mark_as_completed', 'mark_as_in_progress']
    date_hierarchy = 'created_at'
    
    def short_problem(self, obj):
        return obj.problem[:50] + "..." if len(obj.problem) > 50 else obj.problem
    short_problem.short_description = "Problem"
    
    def location(self, obj):
        parts = [f"Block {obj.block.code}"]
        if obj.room:
            parts.append(f"Room {obj.room.number}")
        return " ".join(parts)
    location.short_description = "Location"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f"{updated} requests marked as completed.")
    mark_as_completed.short_description = "Mark selected as completed"
    
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='IN_PROGRESS')
        self.message_user(request, f"{updated} requests marked as in progress.")
    mark_as_in_progress.short_description = "Mark selected as in progress"

@admin.register(MaintenanceLog, site=custom_admin_site)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['request_link', 'technician', 'completion_date', 'labor_hours']
    list_filter = ['technician', 'completion_date']
    search_fields = ['request__problem', 'action_taken']
    readonly_fields = ['completion_date']
    
    def request_link(self, obj):
        url = reverse('admin:infrastructure_maintenancerequest_change', args=[obj.request.id])
        return mark_safe(f'<a href="{url}">{obj.request.problem}</a>')
    request_link.short_description = "Maintenance Request"