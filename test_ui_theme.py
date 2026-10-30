"""Regression checks for the minimal, image-free interface.

No mock statistics or generated illustrations are shown as real vacancy data.
"""
import unittest
from ui_theme import APP_CSS, PALETTE, brand, hero, listing_head
from pathlib import Path


class MinimalUIThemeTests(unittest.TestCase):
    def test_off_grey_background_is_not_black(self):
        self.assertIn("#303338",APP_CSS)
        self.assertIn("#3A3E44",APP_CSS)
        self.assertIn("#F3F4F6",APP_CSS)
        self.assertNotIn("#000000",APP_CSS)
        self.assertEqual(APP_CSS.count("<style>"),1)
        self.assertEqual(APP_CSS.count("</style>"),1)
        self.assertIn(".st-key-top_navigation",APP_CSS)
        self.assertIn("@media(max-width:900px)",APP_CSS)
        self.assertNotRegex(APP_CSS,r"__\w+__")  # every palette token filled in

    def test_matches_billing_app_type_and_cards(self):
        self.assertIn("Barlow Condensed",APP_CSS)
        self.assertIn("Inter",APP_CSS)
        self.assertIn("Outfit",APP_CSS)
        self.assertIn('section[data-testid="stSidebar"]',APP_CSS)
        self.assertIn("border-left:5px solid var(--accent)",APP_CSS)
        self.assertNotIn("#4CC38A",APP_CSS)  # no green accent

    def test_shell_does_not_style_structural_wrappers_as_cards(self):
        self.assertNotIn('[data-testid="stVerticalBlockBorderWrapper"]', APP_CSS)
        self.assertIn('max-width:1280px', APP_CSS)
        self.assertIn('margin-inline:auto', APP_CSS)
        self.assertIn('button:focus-visible', APP_CSS)

    def test_dark_streamlit_theme_and_readable_contrast(self):
        theme=Path(__file__).with_name(".streamlit").joinpath("config.toml").read_text()
        self.assertIn('base = "dark"',theme)
        self.assertIn('backgroundColor = "'+PALETTE["background"]+'"',theme)
        self.assertIn('secondaryBackgroundColor = "'+PALETTE["panel"]+'"',theme)
        self.assertIn('textColor = "'+PALETTE["text"]+'"',theme)
        self.assertIn('primaryColor = "'+PALETTE["accent"]+'"',theme)
        self.assertIn("AI Job Finder",brand("3.1.15"))
        def luminance(hex_color):
            rgb=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
            rgb=[value/12.92 if value<=0.04045 else
                 ((value+.055)/1.055)**2.4 for value in rgb]
            return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
        def contrast(a,b):
            high,low=sorted([luminance(a),luminance(b)],reverse=True)
            return (high+.05)/(low+.05)
        P=PALETTE
        for surface in (P["background"],P["sidebar"],P["panel"],P["raised"]):
            self.assertGreaterEqual(contrast(P["text"],surface),7)
            self.assertGreaterEqual(contrast(P["muted"],surface),4.5)
        self.assertGreaterEqual(contrast(P["accent_bright"],P["panel"]),4.5)
        self.assertGreaterEqual(contrast(P["accent_bright"],P["accent_tint"]),4.5)
        self.assertGreaterEqual(contrast("#FFFFFF",P["accent"]),4.5)

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
