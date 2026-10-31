// 完整的省 / 市 / 区县数据，来源 china-division（pca-code + 港澳台），构建时打包进前端
import pca from 'china-division/dist/pca-code.json'
import extra from 'china-division/dist/HK-MO-TW.json'

const COLLAPSE = new Set(['市辖区', '县', '省直辖县级行政区划', '自治区直辖县级行政区划'])

function buildRegions() {
  const list = []

  for (const province of pca) {
    const cities = new Map()
    for (const city of province.children) {
      const key = COLLAPSE.has(city.name) ? province.name : city.name
      if (!cities.has(key)) cities.set(key, [])
      cities.get(key).push(...(city.children || []).map((area) => area.name))
    }
    list.push({
      name: province.name,
      cities: [...cities].map(([name, districts]) => ({
        name,
        districts: districts.length ? districts : [name]
      }))
    })
  }

  for (const [province, cityMap] of Object.entries(extra)) {
    list.push({
      name: province,
      cities: Object.entries(cityMap).map(([name, districts]) => ({
        name,
        districts
      }))
    })
  }

  return list
}

export const regions = buildRegions()

export function citiesOf(province) {
  return regions.find((row) => row.name === province)?.cities || []
}

export function districtsOf(province, city) {
  return citiesOf(province).find((row) => row.name === city)?.districts || []
}
