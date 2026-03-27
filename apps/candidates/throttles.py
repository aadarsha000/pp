from rest_framework.throttling import SimpleRateThrottle


class ApplicationsPostIPThrottle(SimpleRateThrottle):
    """
    Throttle POST /applications/ to 10 submissions per hour per IP.
    Applies only when the view adds this throttle to throttle_classes.
    """

    rate = "10/hour"

    def get_cache_key(self, request, view):
        ident = request.META.get("REMOTE_ADDR")
        if not ident:
            return None
        return f"throttle:applications_post:{ident}"

