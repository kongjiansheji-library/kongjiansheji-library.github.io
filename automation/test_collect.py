import io,unittest
from unittest.mock import patch
from PIL import Image
import collect
class CollectionTests(unittest.TestCase):
    def test_material_aliases(self):
        for value in ['Wood Floor','Walnut planks','浅色木饰面','高端木纹']:self.assertEqual(collect.classify(value),'木纹')
        self.assertEqual(collect.classify('marble stone'),'大理石')
        self.assertEqual(collect.classify('unknown surface'),'待分类')
    def test_existing_legacy_assets(self):
        ids=collect.existing_ids([{'id':'Tiles141','source':'https://ambientcg.com/view?id=Tiles141'},{'id':'ph_wood_floor'}])
        self.assertIn('ambientcg:Tiles141',ids);self.assertIn('polyhaven:wood_floor',ids)
    def test_source_ids_survive_prefixed_ids(self):
        ids=collect.existing_ids([{'id':'acg_Fabric086','provider_key':'ambientcg','provider_asset_id':'Fabric086'}])
        self.assertIn('ambientcg:Fabric086',ids)
    def test_storage_limit_prevents_writes(self):
        b=io.BytesIO();Image.new('RGB',(10,10)).save(b,'JPEG')
        with self.assertRaisesRegex(ValueError,'storage_budget_reached'):collect.store_image(b.getvalue(),'test',collect.ASSET_BUDGET)
    def test_backfill_walks_beyond_first_catalog_page(self):
        first=[{'assetId':'A'+str(i)} for i in range(250)]
        with patch.object(collect,'getjson',side_effect=[{'foundAssets':first},{'foundAssets':[{'assetId':'OlderAsset'}]}]) as request:
            results=list(collect.ambient_candidates())
        self.assertEqual(len(results),251)
        self.assertEqual(results[-1][0],'OlderAsset')
        self.assertIn('offset=250',request.call_args_list[1].args[0])
    def test_clay_is_classified_without_ai(self):
        self.assertEqual(collect.classify('Clay 009 smooth clay'),'自然地面')
    def test_anchor_parser_excludes_markup(self):
        parser=collect.Anchors();parser.feed('<a href="/textures/wood"><b>Wood</b> floor</a>')
        self.assertEqual(parser.links,[('/textures/wood','Wood  floor')])
    def test_navigation_and_questions_not_material_details(self):
        self.assertFalse(collect.valid_detail('https://x.test/categories/202','材质贴图'))
        self.assertFalse(collect.valid_detail('https://x.test/app/123456','充气材质工具'))
        self.assertFalse(collect.valid_detail('https://x.test/posts/123456','如何获得材质贴图？'))
        self.assertTrue(collect.valid_detail('https://x.test/textures/red-brick','Red brick'))
if __name__=='__main__':unittest.main()
