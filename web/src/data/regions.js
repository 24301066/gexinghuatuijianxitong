// 省 / 市 / 区三级联动用的静态数据（演示用，覆盖常用地区）
export const regions = [
  { name: '北京市', cities: [{ name: '北京市', districts: ['东城区', '西城区', '朝阳区', '海淀区', '丰台区', '通州区', '昌平区'] }] },
  { name: '上海市', cities: [{ name: '上海市', districts: ['黄浦区', '徐汇区', '长宁区', '静安区', '浦东新区', '闵行区', '杨浦区'] }] },
  { name: '天津市', cities: [{ name: '天津市', districts: ['和平区', '河西区', '南开区', '河北区', '滨海新区'] }] },
  { name: '重庆市', cities: [{ name: '重庆市', districts: ['渝中区', '江北区', '南岸区', '沙坪坝区', '九龙坡区', '渝北区'] }] },
  {
    name: '广东省',
    cities: [
      { name: '广州市', districts: ['天河区', '越秀区', '海珠区', '番禺区', '白云区'] },
      { name: '深圳市', districts: ['南山区', '福田区', '罗湖区', '宝安区', '龙岗区'] },
      { name: '佛山市', districts: ['禅城区', '南海区', '顺德区'] },
      { name: '东莞市', districts: ['莞城街道', '南城街道', '东城街道'] }
    ]
  },
  {
    name: '江苏省',
    cities: [
      { name: '南京市', districts: ['玄武区', '秦淮区', '鼓楼区', '建邺区', '江宁区'] },
      { name: '苏州市', districts: ['姑苏区', '工业园区', '吴中区', '相城区'] },
      { name: '无锡市', districts: ['梁溪区', '滨湖区', '新吴区'] }
    ]
  },
  {
    name: '浙江省',
    cities: [
      { name: '杭州市', districts: ['西湖区', '上城区', '拱墅区', '滨江区', '余杭区', '萧山区'] },
      { name: '宁波市', districts: ['海曙区', '江北区', '鄞州区', '镇海区'] },
      { name: '温州市', districts: ['鹿城区', '龙湾区', '瓯海区'] }
    ]
  },
  {
    name: '山东省',
    cities: [
      { name: '济南市', districts: ['历下区', '市中区', '天桥区', '历城区'] },
      { name: '青岛市', districts: ['市南区', '市北区', '李沧区', '崂山区'] },
      { name: '烟台市', districts: ['芝罘区', '福山区', '莱山区'] }
    ]
  },
  {
    name: '四川省',
    cities: [
      { name: '成都市', districts: ['锦江区', '青羊区', '武侯区', '成华区', '高新区'] },
      { name: '绵阳市', districts: ['涪城区', '游仙区', '安州区'] }
    ]
  },
  {
    name: '湖北省',
    cities: [
      { name: '武汉市', districts: ['江岸区', '江汉区', '武昌区', '洪山区', '汉阳区'] },
      { name: '宜昌市', districts: ['西陵区', '伍家岗区', '点军区'] }
    ]
  },
  {
    name: '湖南省',
    cities: [
      { name: '长沙市', districts: ['岳麓区', '芙蓉区', '天心区', '雨花区'] },
      { name: '株洲市', districts: ['天元区', '荷塘区', '石峰区'] }
    ]
  },
  {
    name: '福建省',
    cities: [
      { name: '福州市', districts: ['鼓楼区', '台江区', '仓山区', '晋安区'] },
      { name: '厦门市', districts: ['思明区', '湖里区', '集美区', '海沧区'] },
      { name: '泉州市', districts: ['鲤城区', '丰泽区', '洛江区'] }
    ]
  },
  {
    name: '河南省',
    cities: [
      { name: '郑州市', districts: ['金水区', '二七区', '中原区', '郑东新区'] },
      { name: '洛阳市', districts: ['洛龙区', '西工区', '涧西区'] }
    ]
  },
  {
    name: '河北省',
    cities: [
      { name: '石家庄市', districts: ['长安区', '桥西区', '裕华区', '新华区'] },
      { name: '唐山市', districts: ['路南区', '路北区', '丰润区'] }
    ]
  },
  {
    name: '安徽省',
    cities: [
      { name: '合肥市', districts: ['蜀山区', '庐阳区', '包河区', '瑶海区'] },
      { name: '芜湖市', districts: ['镜湖区', '弋江区', '鸠江区'] }
    ]
  },
  {
    name: '江西省',
    cities: [
      { name: '南昌市', districts: ['东湖区', '西湖区', '青山湖区', '红谷滩区'] },
      { name: '赣州市', districts: ['章贡区', '南康区', '赣县区'] }
    ]
  },
  {
    name: '陕西省',
    cities: [
      { name: '西安市', districts: ['雁塔区', '碑林区', '莲湖区', '未央区', '高新区'] },
      { name: '咸阳市', districts: ['秦都区', '渭城区'] }
    ]
  },
  {
    name: '山西省',
    cities: [
      { name: '太原市', districts: ['小店区', '迎泽区', '杏花岭区', '万柏林区'] },
      { name: '大同市', districts: ['平城区', '云冈区'] }
    ]
  },
  {
    name: '辽宁省',
    cities: [
      { name: '沈阳市', districts: ['和平区', '沈河区', '铁西区', '浑南区'] },
      { name: '大连市', districts: ['中山区', '西岗区', '沙河口区', '甘井子区'] }
    ]
  },
  {
    name: '吉林省',
    cities: [
      { name: '长春市', districts: ['南关区', '朝阳区', '绿园区', '净月区'] },
      { name: '吉林市', districts: ['昌邑区', '船营区', '丰满区'] }
    ]
  },
  {
    name: '黑龙江省',
    cities: [
      { name: '哈尔滨市', districts: ['南岗区', '道里区', '香坊区', '松北区'] },
      { name: '大庆市', districts: ['萨尔图区', '让胡路区'] }
    ]
  },
  {
    name: '云南省',
    cities: [
      { name: '昆明市', districts: ['五华区', '盘龙区', '官渡区', '西山区'] },
      { name: '大理州', districts: ['大理市', '祥云县', '宾川县'] }
    ]
  },
  {
    name: '贵州省',
    cities: [
      { name: '贵阳市', districts: ['南明区', '云岩区', '观山湖区', '花溪区'] },
      { name: '遵义市', districts: ['红花岗区', '汇川区', '播州区'] }
    ]
  },
  {
    name: '广西壮族自治区',
    cities: [
      { name: '南宁市', districts: ['青秀区', '兴宁区', '西乡塘区', '良庆区'] },
      { name: '桂林市', districts: ['秀峰区', '叠彩区', '七星区'] }
    ]
  },
  {
    name: '海南省',
    cities: [
      { name: '海口市', districts: ['龙华区', '美兰区', '琼山区', '秀英区'] },
      { name: '三亚市', districts: ['吉阳区', '天涯区', '海棠区'] }
    ]
  },
  {
    name: '内蒙古自治区',
    cities: [
      { name: '呼和浩特市', districts: ['回民区', '赛罕区', '新城区', '玉泉区'] },
      { name: '包头市', districts: ['昆都仑区', '青山区', '东河区'] }
    ]
  },
  {
    name: '甘肃省',
    cities: [
      { name: '兰州市', districts: ['城关区', '七里河区', '安宁区', '西固区'] },
      { name: '天水市', districts: ['秦州区', '麦积区'] }
    ]
  },
  {
    name: '青海省',
    cities: [
      { name: '西宁市', districts: ['城中区', '城东区', '城西区', '城北区'] },
      { name: '海东市', districts: ['乐都区', '平安区'] }
    ]
  },
  {
    name: '宁夏回族自治区',
    cities: [
      { name: '银川市', districts: ['兴庆区', '金凤区', '西夏区'] },
      { name: '石嘴山市', districts: ['大武口区', '惠农区'] }
    ]
  },
  {
    name: '新疆维吾尔自治区',
    cities: [
      { name: '乌鲁木齐市', districts: ['天山区', '沙依巴克区', '新市区', '水磨沟区'] },
      { name: '克拉玛依市', districts: ['独山子区', '克拉玛依区'] }
    ]
  },
  {
    name: '西藏自治区',
    cities: [
      { name: '拉萨市', districts: ['城关区', '堆龙德庆区', '达孜区'] },
      { name: '日喀则市', districts: ['桑珠孜区', '江孜县'] }
    ]
  },
  { name: '香港特别行政区', cities: [{ name: '香港', districts: ['中西区', '湾仔区', '九龙城区', '沙田区'] }] },
  { name: '澳门特别行政区', cities: [{ name: '澳门', districts: ['花地玛堂区', '圣安多尼堂区', '大堂区'] }] },
  { name: '台湾省', cities: [{ name: '台北市', districts: ['中正区', '信义区', '大安区'] }, { name: '高雄市', districts: ['苓雅区', '左营区'] }] }
]

export function citiesOf(province) {
  return regions.find((row) => row.name === province)?.cities || []
}

export function districtsOf(province, city) {
  return citiesOf(province).find((row) => row.name === city)?.districts || []
}
