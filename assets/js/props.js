/* ============================================================
   道具与词 —— 全站的视觉核心
   每一页的巨型标题 = 一个粉色的词 + 一个 3D 物件从词中间穿过去
   ★ 改道具只改这个文件
   ============================================================ */

const PROPS = {
  camera:   'assets/props/camera.png',
  player:   'assets/props/player.png',
  books:    'assets/props/books.png',
  envelope: 'assets/props/envelope.png',
  portrait: 'assets/img/portrait-cut.png'
};

/* 五个章节页的巨词与穿过它的物件
   px / py  物件在词上的落点（50% = 正中）
   rot      静止时的倾斜角
   ph       物件高度 = 字高 × ph  —— 缩放跟着字号走，不跟页面走 */
const CHAPTERS = {
  work:    { word:'作品', en:'Selected Work',      prop:'camera',   px:'50%', py:'53%', rot:-6, ph:1.42 },
  screen:  { word:'影音', en:'On the Screen',      prop:'player',   px:'51%', py:'50%', rot: 5, ph:1.30 },
  words:   { word:'文字', en:'Written',            prop:'books',    px:'49%', py:'57%', rot:-4, ph:1.12 },
  about:   { word:'关于', en:'This is Me',         prop:'portrait', px:'50%', py:'50%', rot:-4, ph:1.10, sticker:true },
  contact: { word:'联系', en:'Say Hello',          prop:'envelope', px:'50%', py:'53%', rot: 5, ph:1.22 }
};

/* 项目详情页顶部的小道具：按项目分类换 */
const PROP_BY_CAT = {
  media:    'books',
  design:   'camera',
  av:       'player',
  strategy: 'envelope',
  research: 'books',
  aigc:     'player',
  latest:   'camera'
};

/* 顶层 const 不挂 window，显式挂一份给其它脚本用 */
window.PROPS = PROPS;
window.CHAPTERS = CHAPTERS;
window.PROP_BY_CAT = PROP_BY_CAT;
