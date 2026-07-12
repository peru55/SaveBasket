from django.core.management.base import BaseCommand

from products.confirmed_duplicate_repair import (
    apply_confirmed_duplicate_repairs,
    plan_confirmed_duplicate_repairs,
)


class Command(BaseCommand):
    help = "Repair the two explicitly confirmed duplicate product pairs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag the command is read-only.",
        )

    def handle(self, *args, **options):
        if not options["apply"]:
            plans = plan_confirmed_duplicate_repairs()
            ready = sum(plan.status == "ready" for plan in plans)
            ambiguous = sum(plan.status == "ambiguous" for plan in plans)
            missing = sum(plan.status == "missing" for plan in plans)
            canonical_only = sum(plan.status == "canonical_only" for plan in plans)
            self.stdout.write("DRY RUN — no database changes were made.")
            for plan in plans:
                self.stdout.write(f"[{plan.status.upper()}] {plan.pair.label}")
            self.stdout.write(
                f"Ready: {ready}; Missing/already repaired: {missing}; "
                f"Canonical-only: {canonical_only}; Ambiguous: {ambiguous}"
            )
            return

        result = apply_confirmed_duplicate_repairs()
        self.stdout.write("APPLIED — confirmed duplicate repair transaction completed.")
        self.stdout.write(
            f"Merged: {result.merged}; Skipped: {result.skipped}; "
            f"Metadata normalized: {result.normalized}; Ambiguous: {result.ambiguous}"
        )
