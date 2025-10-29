from __future__ import annotations

from collections import Counter, defaultdict

from app.models.store import Store


class AnalyticsService:
    """Aggregations for dashboards and staff analytics."""

    @staticmethod
    def analytics_summary():
        store = Store.instance()
        veh_counts: dict[str, int] = {}
        revenue = 0.0
        for r in store.rentals.values():
            veh_counts[r["vehicle_id"]] = veh_counts.get(r["vehicle_id"], 0) + 1
            revenue += float(r.get("total", 0))
        top = sorted(veh_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        bottom = sorted(veh_counts.items(), key=lambda x: x[1])[:5]
        return {
            "total_vehicles": len(store.vehicles),
            "total_users": len(store.users),
            "total_rentals": len(store.rentals),
            "revenue": round(revenue, 2),
            "most_rented": top,
            "least_rented": bottom,
        }

    @staticmethod
    def analytics():
        store = Store.instance()

        # Totals
        total_users = len(store.users)
        total_vehicles = len(store.vehicles)
        total_rentals = len(store.rentals)
        revenue = round(sum((r.get("total") or 0) for r in store.rentals.values()), 2)

        # Rentals per vehicle
        cnt = Counter([r.get("vehicle_id") for r in store.rentals.values()])
        rentals_by_vehicle = []
        for vid, v in store.vehicles.items():
            label = f"{v.get('brand', '')} {v.get('model', '')}".strip()
            rentals_by_vehicle.append({
                "vehicle_id": vid,
                "label": label or vid[:6],
                "count": cnt.get(vid, 0),
            })
        rentals_by_vehicle.sort(key=lambda x: x["count"], reverse=True)

        # Revenue by date (group by rental start_date)
        rev_by_date = defaultdict(float)
        for r in store.rentals.values():
            d = r.get("start_date")
            if not d:
                continue
            rev_by_date[d] += float(r.get("total") or 0)
        revenue_by_date = [{"date": k, "total": round(v, 2)} for k, v in sorted(rev_by_date.items())]

        # Users by role
        role_cnt = Counter([u.get("role", "") for u in store.users.values()])
        users_by_role = [{"role": k or "unknown", "count": v} for k, v in role_cnt.items()]

        return {
            "totals": {
                "users": total_users,
                "vehicles": total_vehicles,
                "rentals": total_rentals,
                "revenue": revenue,
            },
            "rentals_by_vehicle": rentals_by_vehicle,
            "revenue_by_date": revenue_by_date,
            "users_by_role": users_by_role,
        }
