from django.shortcuts import redirect, render


def allowed_users(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            user_groups = [group.name for group in request.user.groups.all()]

            if any(role in user_groups for role in allowed_roles):
                return view_func(request, *args, **kwargs)
            else:
                return render(request, 'accueil/denied.html')
        return wrapper_func
    return decorator