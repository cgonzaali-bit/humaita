from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def role_required(*roles):
    """
    Decorador que restringe el acceso según el rol del usuario.
    Uso: @role_required('SUPER_ADMIN', 'ADMIN')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied('No tienes permisos para acceder a esta sección.')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Solo SUPER_ADMIN y ADMIN."""
    return role_required('SUPER_ADMIN', 'ADMIN')(view_func)


def super_admin_required(view_func):
    """Solo SUPER_ADMIN (dueño)."""
    return role_required('SUPER_ADMIN')(view_func)


def instructor_required(view_func):
    """SUPER_ADMIN, ADMIN e INSTRUCTOR."""
    return role_required('SUPER_ADMIN', 'ADMIN', 'INSTRUCTOR')(view_func)
