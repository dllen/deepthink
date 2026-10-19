import { last30daysSources } from '../assets/last30days-sources';

/**
 * 构建搜索 URL
 * @param {string} query - 搜索关键词
 * @param {string} urlTemplate - URL 模板，{q} 会被替换
 * @returns {string} 编码后的搜索 URL
 */
export const buildSearchUrl = (query, urlTemplate) => {
  return urlTemplate.replace('{q}', encodeURIComponent(query));
};

/**
 * 批量构建所有信息源的搜索 URL
 * @param {string} query - 搜索关键词
 * @returns {Object} { sourceId: url } 映射
 */
export const buildAllSearchUrls = (query) => {
  return last30daysSources.reduce((acc, source) => {
    acc[source.id] = buildSearchUrl(query, source.url);
    return acc;
  }, {});
};
