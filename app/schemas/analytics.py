from pydantic import BaseModel

class AdminDashboardResponse(BaseModel):
    active_subscriptions: int
    lunch_meal_prep_count: int
    dinner_meal_prep_count: int
    active_drivers_count: int
    unassigned_routes_count: int
