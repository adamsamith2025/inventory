from rest_framework.permissions import BasePermission
from authentication.permissions import HasModulePermission as BaseHasModulePermission

class HasModulePermission(BaseHasModulePermission):
    module_name = 'inventory' 