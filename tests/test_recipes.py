import unittest
from recipes import get_recipe, format_recipe, calculate_crafting_materials

class TestRecipes(unittest.TestCase):
    def test_get_recipe(self):
        # Test existing recipe
        recipe = get_recipe("iron ingot")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["station"], "Smelter")
        self.assertEqual(recipe["skill"], "Smelting")
        
        # Test non-existent recipe
        recipe = get_recipe("nonexistent item")
        self.assertIsNone(recipe)
        
        # Test case insensitivity
        recipe = get_recipe("IRON INGOT")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["station"], "Smelter")

    def test_format_recipe(self):
        recipe = get_recipe("iron ingot")
        formatted = format_recipe(recipe)
        self.assertIsNotNone(formatted)
        self.assertIn("Smelter", formatted)
        self.assertIn("4 Iron Ore", formatted)

        # Test with None recipe
        formatted = format_recipe(None)
        self.assertIsNone(formatted)

    def test_calculate_crafting_materials_simple(self):
        # Test simple recipe (iron ingot)
        materials = calculate_crafting_materials("iron ingot")
        self.assertEqual(materials, {"iron ore": 4})
        
        # Test with quantity
        materials = calculate_crafting_materials("iron ingot", quantity=2)
        self.assertEqual(materials, {"iron ore": 8})

    def test_calculate_crafting_materials_complex(self):
        # Test recipe with intermediate items (steel ingot)
        materials = calculate_crafting_materials("steel ingot")
        expected = {
            "iron ore": 12,  # 3 iron ingots × 4 iron ore each
            "charcoal": 1,
            "flux": 1
        }
        self.assertEqual(materials, expected)
        
        # Test with intermediate items included
        materials = calculate_crafting_materials("steel ingot", include_intermediate=True)
        expected = {
            "iron ore": 12,
            "charcoal": 1,
            "flux": 1,
            "iron ingot": 3
        }
        self.assertEqual(materials, expected)

    def test_calculate_crafting_materials_nonexistent(self):
        # Test with non-existent recipe
        materials = calculate_crafting_materials("nonexistent item")
        self.assertIsNone(materials)

if __name__ == '__main__':
    unittest.main()