"""Regression checks for the minimal, image-free interface.

No mock statistics or generated illustrations are shown as real vacancy data.
"""
import unittest
from ui_theme import APP_CSS, brand, hero, listing_head


class MinimalUIThemeTests(unittest.TestCase):
    def test_theme_is_light_legible_and_padded(self):
        self.assertIn("#F5F7F5",APP_CSS)
        self.assertIn("#146B54",APP_CSS)
        self.assertIn('background:var(--paper)',APP_CSS)
        self.assertIn('padding:1.5rem 1.65rem',APP_CSS)
        self.assertIn('.st-key-top_navigation',APP_CSS)
        self.assertIn("@media(max-width:900px)",APP_CSS)

    def test_modular_geometry_and_white_text_on_dark_green(self):
        # Override block intentionally comes after old soft-panel rules.
        self.assertIn("October 16 modular pass",APP_CSS)
        self.assertIn("border-radius:4px!important",APP_CSS)
        self.assertIn("border-radius:3px!important",APP_CSS)
        self.assertIn("border-radius:2px!important",APP_CSS)
        self.assertIn("padding:1.95rem 2.1rem",APP_CSS)
        self.assertIn("job-module-heading",APP_CSS)
        self.assertIn("label:has(input:checked) *",APP_CSS)
        self.assertIn('[data-testid="stDownloadButton"] button *',APP_CSS)
        self.assertIn("color:#FFFFFF!important",APP_CSS)
        self.assertIn("-webkit-text-fill-color:#FFFFFF!important",APP_CSS)
        self.assertIn("background:var(--forest)!important",APP_CSS)

    def test_no_green_outlines_or_panel_borders(self):
        section=APP_CSS.split('No colored module outlines.')[-1]
        self.assertIn('border:0!important',section)
        self.assertIn('border-left:0!important',section)
        self.assertIn('border-top:0!important',section)
        self.assertIn('border-bottom:0!important',section)
        self.assertIn('box-shadow:0 3px 16px rgba(',section)
        self.assertIn('stVerticalBlockBorderWrapper',section)
        self.assertIn('stMetric',section)
        self.assertIn('stForm',section)
        self.assertIn('label:has(input:checked)',section)
        self.assertIn('background:#FFFFFF!important',section)
        self.assertIn('color:#FFFFFF!important',section)

    def test_no_generated_briefcase_or_stock_art(self):
        self.assertNotIn("<img",APP_CSS+brand())
        self.assertNotIn("briefcase",APP_CSS.casefold()+brand().casefold())
        self.assertNotIn("svg",APP_CSS.casefold()+brand().casefold())
        self.assertIn("AI Job Finder",brand())
        self.assertIn("Version 3.1.13",brand("3.1.13"))

    def test_listing_uses_data_not_mock_values(self):
        listing=listing_head("Partnership Director","Future Publishing",
                              "New York, NY","On-site",False,94,
                              is_new=True,verify=True,direct=True)
        self.assertIn("94",listing)
        self.assertIn(" / 96",listing)
        self.assertIn("Verify requirements",listing)
        self.assertIn("Future Publishing",listing)
        self.assertIn("New",listing)
        self.assertNotIn("1,248",listing)
        self.assertNotIn("92%",listing)

    def test_listing_dynamic_text_escaped(self):
        listing=listing_head("<script>alert(1)</script>",
                             "Big & Small Co.","Seattle <WA>",
                             "Hybrid",True,91)
        self.assertNotIn("<script>",listing)
        self.assertIn("&lt;script&gt;",listing)
        self.assertIn("Big &amp; Small",listing)
        self.assertIn("&lt;WA&gt;",listing)

    def test_restricted_listing_warns_on_compact_card(self):
        listing=listing_head("Coordinator", "Example","Minot, ND","On-site",
                              True,50,restricted=True,direct=False)
        self.assertIn("Internal only",listing)
        self.assertNotIn("Direct employer",listing)

    def test_simple_hero_has_no_verbiage_or_generated_art(self):
        markup=hero("Find Jobs","Nationwide · On-site & hybrid · 45 days")
        self.assertIn("Find Jobs",markup)
        self.assertNotIn("<img",markup)
        self.assertLess(len(markup),350)


if __name__=="__main__":
    unittest.main()
