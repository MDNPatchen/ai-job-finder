"""Regression checks for the minimal, image-free interface.

No mock statistics or generated illustrations are shown as real vacancy data.
"""
import unittest
from ui_theme import APP_CSS, PALETTE, brand, hero, listing_head
from pathlib import Path


class MinimalUIThemeTests(unittest.TestCase):
    def test_slate_background_is_dark_not_black(self):
        self.assertIn("#27342F",APP_CSS)
        self.assertIn("#34443D",APP_CSS)
        self.assertIn("#F1F6F2",APP_CSS)
        self.assertNotIn("#0B1114",APP_CSS)
        self.assertEqual(APP_CSS.count("<style>"),1)
        self.assertEqual(APP_CSS.count("</style>"),1)
        self.assertIn(".st-key-top_navigation",APP_CSS)
        self.assertIn("@media(max-width:900px)",APP_CSS)

    def test_compact_modules_have_smaller_interiors_without_green_borders(self):
        self.assertIn("Compact independent modules:",
                      APP_CSS)
        self.assertIn("padding:1.18rem 1.38rem",APP_CSS)
        self.assertIn("padding:1.12rem 1.32rem",APP_CSS)
        self.assertIn("padding:1.45rem 1.65rem",APP_CSS)
        self.assertIn("min-height:105px",APP_CSS)
        self.assertIn("min-height:40px",APP_CSS)
        self.assertIn("font-size:1.10rem",APP_CSS)
        self.assertIn("font-size:.71rem",APP_CSS)
        self.assertIn("border:0!important",APP_CSS)
        self.assertNotIn("border-left:4px",APP_CSS)
        self.assertNotIn("border-top:3px",APP_CSS)
        self.assertIn("background:var(--paper)",APP_CSS)

    def test_roomier_modules_have_balanced_side_margins(self):
        self.assertIn("max-width:1370px",APP_CSS)
        self.assertIn("width:calc(100% - 8rem)",APP_CSS)
        self.assertIn("margin-left:auto!important",APP_CSS)
        self.assertIn("margin-right:auto!important",APP_CSS)
        self.assertIn("padding:2rem 3rem 4rem",APP_CSS)
        self.assertIn("width:100%!important;max-width:100%!important",APP_CSS)
        self.assertIn("min-height:105px",APP_CSS)
        self.assertIn("min-height:40px",APP_CSS)
        self.assertNotIn("border-left:4px",APP_CSS)

    def test_green_filled_controls_keep_white_text(self):
        self.assertIn("label:has(input:checked) *",APP_CSS)
        self.assertIn('[data-testid="stDownloadButton"] button *',APP_CSS)
        self.assertIn("color:#FFFFFF!important",APP_CSS)
        self.assertIn("-webkit-text-fill-color:#FFFFFF!important",APP_CSS)
        self.assertIn("background:var(--forest)!important",APP_CSS)

    def test_dark_streamlit_theme_and_readable_contrast(self):
        theme=Path(__file__).with_name(".streamlit").joinpath("config.toml").read_text()
        self.assertIn('base = "dark"',theme)
        self.assertIn('backgroundColor = "#27342F"',theme)
        self.assertIn('secondaryBackgroundColor = "#34443D"',theme)
        self.assertIn('textColor = "#F1F6F2"',theme)
        self.assertIn("Compact Slate",brand("3.1.15"))
        self.assertEqual(PALETTE["background"],"#27342F")
        self.assertEqual(PALETTE["panel"],"#34443D")
        def luminance(hex_color):
            rgb=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
            rgb=[value/12.92 if value<=0.04045 else
                 ((value+.055)/1.055)**2.4 for value in rgb]
            return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
        def contrast(a,b):
            high,low=sorted([luminance(a),luminance(b)],reverse=True)
            return (high+.05)/(low+.05)
        self.assertGreaterEqual(contrast("#F1F6F2","#34443D"),7)
        self.assertGreaterEqual(contrast("#BBCDC2","#34443D"),4.5)
        self.assertGreaterEqual(contrast("#FFFFFF","#257B5B"),4.5)

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
