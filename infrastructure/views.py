from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import MaintenanceRequest, Equipment, Block, Floor, Room
from .forms import MaintenanceRequestForm
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q
from django.core.mail import send_mail
import os

# @login_required
def home(request):
    blocks = Block.objects.all()
    if request.user.is_authenticated:
        user_requests = MaintenanceRequest.objects.filter(reported_by=request.user)
        completed_requests = user_requests.filter(status='COMPLETED')
        in_progress_requests = user_requests.filter(status='IN_PROGRESS')
        
        return render(request, 'infrastructure/home.html', {
            'blocks': blocks,
            'user_requests': user_requests,
            'completed_requests': completed_requests,
            'in_progress_requests': in_progress_requests,
        })
    return render(request, 'infrastructure/home.html', {'blocks': blocks})

@login_required
def my_issues(request):
    issues = MaintenanceRequest.objects.filter(reported_by=request.user).order_by('-created_at')
    return render(request, "infrastructure/my_issues.html", {"issues": issues})


@login_required
def issue_detail(request, pk):
    issue = get_object_or_404(MaintenanceRequest, pk=pk, reported_by=request.user)
    return render(request, 'infrastructure/issue_detail.html', {'issue': issue})

@login_required
def report_issue(request):
    blocks = Block.objects.all()
    
    if request.method == "POST":
        form = MaintenanceRequestForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                maintenance_request = form.save(commit=False)
                maintenance_request.reported_by = request.user
                
                # Handle equipment assignment
                equipment_name = form.cleaned_data['equipment_name']
                model_number = form.cleaned_data.get('model_number')
                serial_number = form.cleaned_data.get('serial_number')
                room = form.cleaned_data['room']
                quantity = form.cleaned_data.get('quantity', 1)
                
                if model_number and serial_number:
                    equipment = Equipment.objects.get(
                        room=room,
                        name=equipment_name,
                        model_number=model_number,
                        serial_number=serial_number
                    )
                    maintenance_request.equipment = equipment
                
                # If serial number provided
                elif serial_number:
                    equipment = Equipment.objects.get(
                        room=room,
                        name=equipment_name,
                        serial_number=serial_number
                    )
                    maintenance_request.equipment = equipment
                    maintenance_request.quantity = 1
                
                # If only model number provided
                elif model_number:
                    # Assign the first matching equipment (or could create a relation table)
                    # equipment = Equipment.objects.filter(
                    #     room=room,
                    #     name=equipment_name,
                    #     model_number=model_number
                    # ).first()
                    # if equipment:
                    # maintenance_request.equipment = equipment
                    maintenance_request.quantity = quantity
                else:
                    maintenance_request.quantity = quantity
                        
                maintenance_request.save()
                send_mail(
                subject="Issue Report Submitted",
                message=f"Dear {request.user.username},\n\nYour issue report has been successfully submitted. Our team will review it soon.",
                from_email=os.getenv('MAIL_HOST_USER'),
                recipient_list=[os.getenv('MAIL_HOST_USER')], #valid email just for testing should be [request.user.email]
                fail_silently=False,
                )
                
                messages.success(request, "Your maintenance request has been submitted successfully!")
                return redirect('home')
            except Equipment.DoesNotExist:
                form.add_error(None, 'The specified equipment was not found')
            except Exception as e:
                form.add_error(None, f'An error occurred: {str(e)}')
    else:
        form = MaintenanceRequestForm(user=request.user)
    
    return render(request, "infrastructure/report_issue.html", {
        "form": form,
        "blocks": blocks,
    })

def ajax_load_floors(request):
    block_id = request.GET.get('block')
    if not block_id:
        return JsonResponse({'html': '<option value="">Select a Floor</option>'})
    
    try:
        block = Block.objects.get(id=block_id)
        if not block.has_multiple_floors:
            return JsonResponse({'html': '<option value="">This block has no floors</option>'})
            
        floors = Floor.objects.filter(block_id=block_id).order_by('number')
        context = {'floors': floors}
        html = render_to_string('infrastructure/floor_dropdown_options.html', context)
        return JsonResponse({'html': html})
    except Exception as e:
        return JsonResponse({'html': f'<option value="">Error: {str(e)}</option>'})

def ajax_load_rooms(request):
    block_id = request.GET.get('block')
    floor_id = request.GET.get('floor')
    
    if not block_id:
        return JsonResponse({'html': '<option value="">Select a Room</option>'})
    
    try:
        rooms = Room.objects.filter(block_id=block_id)
        if floor_id:
            rooms = rooms.filter(floor_id=floor_id)
        else:
            # For blocks without floors
            rooms = rooms.filter(floor__isnull=True)
            
        rooms = rooms.order_by('number')
        context = {'rooms': rooms}
        html = render_to_string('infrastructure/room_dropdown_options.html', context)
        return JsonResponse({'html': html})
    except Exception as e:
        return JsonResponse({'html': f'<option value="">Error: {str(e)}</option>'})

def ajax_load_equipment(request):
    room_id = request.GET.get('room')
    if not room_id:
        return JsonResponse({'html': '<option value="">Select Equipment</option>'})
    
    try:
        # Get distinct equipment names in this room
        equipment_names = Equipment.objects.filter(room_id=room_id)\
                               .order_by('name')\
                               .values_list('name', flat=True)\
                               .distinct()
        context = {'equipment_names': equipment_names}
        html = render_to_string('infrastructure/equipment_dropdown_options.html', context)
        return JsonResponse({'html': html})
    except Exception as e:
        return JsonResponse({'html': f'<option value="">Error loading equipment</option>'})

def ajax_load_equipment_by_block(request):
    block_id = request.GET.get('block')
    if not block_id:
        return JsonResponse({'html': '<option value="">Select Equipment</option>'})
    
    try:
        # Get distinct equipment names in this block
        equipment_names = Equipment.objects.filter(block_id=block_id)\
                               .order_by('name')\
                               .values_list('name', flat=True)\
                               .distinct()
        context = {'equipment_names': equipment_names}
        html = render_to_string('infrastructure/equipment_dropdown_options.html', context)
        return JsonResponse({'html': html})
    except Exception as e:
        return JsonResponse({'html': f'<option value="">Error loading equipment</option>'})
    
def ajax_load_equipment_by_floor(request):
    floor_id = request.GET.get('floor')
    if  not floor_id:
        return JsonResponse({'html': '<option value="">Select Equipment</option>'})
    
    try:
        # Get distinct equipment names in this floor
        equipment_names = Equipment.objects.filter(floor_id=floor_id)\
                               .order_by('name')\
                               .values_list('name', flat=True)\
                               .distinct()
        context = {'equipment_names': equipment_names}
        html = render_to_string('infrastructure/equipment_dropdown_options.html', context)
        return JsonResponse({'html': html})
    except Exception as e:
        return JsonResponse({'html': f'<option value="">Error loading equipment</option>'})
    
def ajax_load_equipment_details(request):
    equipment_name = request.GET.get('equipment')
    room_id = request.GET.get('room')
    floor_id = request.GET.get('floor')
    block_id = request.GET.get('block')

    if not equipment_name:
        return JsonResponse({'error': 'Missing equipment name'}, status=400)
    
    if not (room_id or floor_id or block_id):
        return JsonResponse({'error': 'At least one location filter (room, floor, or block) is required.'}, status=400)

    try:
        # Start base query with mandatory equipment name
        queryset = Equipment.objects.filter(name=equipment_name)

        # Apply available location filters
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        elif floor_id:
            queryset = queryset.filter(floor_id=floor_id)
        elif block_id:
            queryset = queryset.filter(block_id=block_id)

        # Exclude incomplete entries
        queryset = queryset.exclude(
            Q(model_number__isnull=True) | Q(model_number__exact='') |
            Q(serial_number__isnull=True) | Q(serial_number__exact='')
        )

        # Get unique models and serials
        models = list(set(e.model_number for e in queryset if e.model_number))
        serials = list(set(e.serial_number for e in queryset if e.serial_number))

        context = {
            'models': models,
            'serials': serials
        }

        html = render_to_string('infrastructure/ajax_load_equipment_details.html', context)
        return JsonResponse({'html': html})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def ajax_get_equipment_count(request):
    room_id = request.GET.get('room')
    equipment_name = request.GET.get('name')
    model_number = request.GET.get('model')
    
    if not room_id or not equipment_name:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        equipments = Equipment.objects.filter(
            room_id=room_id,
            name=equipment_name
        )
        
        if model_number:
            equipments = equipments.filter(model_number=model_number)
        
        count = equipments.count()
        return JsonResponse({'count': count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)