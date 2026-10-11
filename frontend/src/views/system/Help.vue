<template>
  <div class="help-wrap">
    <div class="help-tabs">
      <div v-for="t in TABS" :key="t.key" class="htab" :class="{ active: tab === t.key }" @click="tab = t.key">{{ t.label }}</div>
    </div>

    <div class="help-body">
      <!-- 图标详解 -->
      <template v-if="tab === 'icons'">
        <h3>先看懂大逻辑（打个比方：像开店）</h3>
        <p>主页图标按 <b>单据 → 报表 → 资料 → 系统</b> 四排排列，正好就是使用顺序：</p>
        <ul>
          <li><b>第1步 · 建档案</b>（资料排）：先把货物、仓库、库位、往来单位、进出类别、工作人员这些"家底信息"登记好。档案不建，后面单据就没得选。</li>
          <li><b>第2步 · 录家底</b>：用"期初库存"把仓库里现有的货一次性录进去，作为起步账。</li>
          <li><b>第3步 · 天天记账</b>（单据排）：以后每天只做两件事——货进来录<b>入库单</b>，货出去录<b>出库单</b>；搬仓库录<b>调拨单</b>，定期对账录<b>盘点单</b>。</li>
          <li><b>第4步 · 看账本</b>（报表排）：库存、进销存、利润……这些<b>全部自动算好</b>，你只管看、管查。</li>
          <li><b>第5步 · 日常维护</b>（系统排）：定期<b>备份</b>，给员工开<b>账号</b>，出问题看<b>操作日志</b>。</li>
        </ul>
        <p>下面逐个图标详细说明。</p>
        <div v-for="g in ICON_GROUPS" :key="g.name">
          <h3>{{ g.name }}</h3>
          <div class="ic-grid">
            <div class="ic-card" v-for="it in g.items" :key="it.n">
              <div class="ic-side"><span class="ic-emoji">{{ it.ic }}</span><span class="ic-name">{{ it.n }}</span></div>
              <div class="ic-txt"><b class="ic-one">{{ it.one }}</b><span v-html="it.d"></span></div>
            </div>
          </div>
        </div>
      </template>

      <!-- 软件简介 -->
      <template v-else-if="tab === 'intro'">
        <h3>软件简介</h3>
        <p>本系统是一套<b>仓库进出存管理软件</b>（Web 版），覆盖仓库日常业务的全部流程：基础资料 → 期初建账 → 进出单据 → 实时库存与报表分析。数据集中保存在<b>服务器数据库</b>中，支持局域网内多台电脑同时使用，所有数据操作均记录服务器日志，不在浏览器保存业务数据。</p>
        <h3>主要特点</h3>
        <ul>
          <li><b>单据驱动</b>：入库单、出库单、调拨单、盘点单、期初库存，保存后库存即时更新，账实一致。</li>
          <li><b>实时核算</b>：移动加权平均法核算成本，进销存、利润分析等报表实时汇总，无需手工结转。</li>
          <li><b>权限管理</b>：每个账号可单独设置操作权限，未授权的功能不显示、不可进入。</li>
          <li><b>主题换肤</b>：系统设置中可切换 白色 / 绿色 / 蓝青 三种界面主题。</li>
          <li><b>数据安全</b>：支持备份 / 还原 / 初始化，所有增删改操作写入服务器操作日志。</li>
        </ul>
        <h3>界面说明</h3>
        <ul>
          <li>左上角三个指示灯：<span class="dot g"></span>绿色闪烁=与服务器连接正常；<span class="dot y"></span>黄色闪烁=正在通讯；<span class="dot r"></span>红色闪烁=连接断开。</li>
          <li>主页分四排功能：单据（整页窗口）、报表（整页窗口）、资料（弹窗）、系统（弹窗）。</li>
          <li>右上角显示登录账号与系统版本，可退出登录。</li>
        </ul>
      </template>

      <!-- 功能思维导图 -->
      <template v-else-if="tab === 'map'">
        <h3>功能思维导图</h3>
        <div class="mindmap">
          <svg class="mm-svg" :viewBox="mm.viewBox" role="img" aria-label="功能思维导图">
            <!-- 连接线：干线 / 分支→功能 / 功能→说明 -->
            <path v-for="(p, i) in mm.trunks" :key="'t' + i" :d="p.d" :stroke="p.color" stroke-width="3.6" />
            <path v-for="(p, i) in mm.links" :key="'l' + i" :d="p.d" :stroke="p.color" stroke-width="1.8" />
            <path v-for="(p, i) in mm.tipLinks" :key="'p' + i" :d="p.d" :stroke="p.color" stroke-width="1" />

            <!-- 功能节点与说明子节点 -->
            <g v-for="(leaf, i) in mm.leaves" :key="'f' + i">
              <rect class="mm-leaf-box" :x="leaf.x" :y="leaf.y" :width="leaf.w" :height="leaf.h" rx="8" ry="8" :stroke="leaf.color" />
              <text class="mm-leaf-name" :x="leaf.x + 30" :y="leaf.y + 18" :fill="leaf.color">{{ leaf.label }}</text>
              <text class="mm-leaf-ic" :x="leaf.x + 9" :y="leaf.y + 18">{{ leaf.ic }}</text>
              <foreignObject :x="leaf.x + 8" :y="leaf.y + 21" :width="leaf.w - 16" :height="leaf.h - 21" class="mm-fo">
                <div xmlns="http://www.w3.org/1999/xhtml" class="mm-leaf-tip">{{ leaf.tip }}</div>
              </foreignObject>
            </g>

            <!-- 四条主分支 -->
            <g v-for="(b, i) in mm.branches" :key="'b' + i">
              <rect class="mm-branch-box" :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="9" ry="9" :fill="b.color" />
              <text class="mm-branch-name" :x="b.x + b.w / 2" :y="b.y + b.h / 2 + 5" fill="#fff">{{ b.name }}</text>
            </g>

            <!-- 中心主题 -->
            <g>
              <rect class="mm-root-box" :x="mm.root.x" :y="mm.root.y" :width="mm.root.w" :height="mm.root.h" rx="12" ry="12" />
              <text class="mm-root-name" :x="mm.root.x + mm.root.w / 2" :y="mm.root.y + mm.root.h / 2 + 7" :fill="accent">🏭 仓库管理系统</text>
            </g>
          </svg>
        </div>
      </template>

      <!-- 快速上手 -->
      <template v-else-if="tab === 'start'">
        <h3>快速上手（五步建账）</h3>
        <div class="steps">
          <div class="step" v-for="(s, i) in STEPS" :key="i">
            <div class="step-no">{{ i + 1 }}</div>
            <div class="step-txt"><b>{{ s.t }}</b><span>{{ s.d }}</span></div>
          </div>
        </div>
        <h3>日常操作流程</h3>
        <ul>
          <li><b>入库</b>：主页 → 单据 → 入库单 → 点表头"往来单位/仓库/类别"框弹资料窗选取（可现场添加）→ 双击选择货物、填数量单价 → 保存。库存即时增加。</li>
          <li><b>表头选取（所有单据一致）</b>：点击表头 往来单位/进出类别/收发货仓库 框，弹出对应资料窗口（左侧分类树＋右侧列表＋添加/编辑/选取）；点击底部 供货人/领货人/经办人/审核人 等，弹「工作人员」窗口选取；双击行内"编码"弹货物资料、"库位"弹库区库位，编码/库位也可直接输入名称回车带出。</li>
          <li><b>出库</b>：出库单同上。库存不足时系统会提示，成本按移动加权平均自动计算。</li>
          <li><b>调拨</b>：调拨单选择调出仓库/库位与调入仓库/库位，货物位置即时转移。</li>
          <li><b>盘点</b>：盘点单录入账面数量与实际数量，系统自动计算盈亏数量与金额并调整库存。</li>
          <li><b>借还</b>：借出/归还登记，借还统计报表可查待还数量。</li>
        </ul>
        <h3>报表使用</h3>
        <ul>
          <li>报表窗口点击「查询」可按期间/仓库/关键字过滤；「预览/打印」可打印；「导出」可导出 CSV 用 Excel 打开。</li>
          <li>报表为只读查询（与原版一致）：如需修改最低/最高库存、备注，请到「货物资料」里编辑货物。</li>
        </ul>
      </template>

      <!-- 模块说明 -->
      <template v-else-if="tab === 'modules'">
        <h3>模块说明</h3>
        <div class="mod" v-for="m in MODULES" :key="m.t">
          <div class="mod-t">{{ m.t }}</div>
          <div class="mod-d">{{ m.d }}</div>
        </div>
      </template>

      <!-- 数据与安全 -->
      <template v-else>
        <h3>数据保存与安全</h3>
        <ul>
          <li>所有资料、单据、报表、<b>操作日志</b>均保存在<b>服务器数据库</b>（容器数据卷持久化），浏览器不保存任何业务数据，换电脑登录数据完全一致。</li>
          <li><b>操作日志</b>：登录、资料增删改、单据保存/删除、设置修改、备份还原、初始化等全部操作自动记录（时间、账号、模块、操作、详情），管理员可在 系统 → 操作日志 中查询。</li>
          <li><b>备份</b>：建议定期在 系统 → 备份 中下载数据库文件，妥善保存。</li>
          <li><b>还原</b>：选择备份文件可整体恢复数据，<span class="warn">还原会覆盖当前全部数据</span>。</li>
          <li><b>初始化</b>：可按勾选项清空业务数据或全部数据（保留账号），操作前请先备份。</li>
          <li><b>账号权限</b>：为每个员工建立独立账号并按需勾选操作权限，禁用账号立即失效。</li>
        </ul>
        <h3>常见问题</h3>
        <ul>
          <li><b>打不开页面？</b>看左上角指示灯：红灯说明服务器未启动或网络不通，检查服务器容器与局域网连接。</li>
          <li><b>忘记密码？</b>联系管理员在 账号权限 中重置。</li>
          <li><b>单号规则？</b>系统设置 → 对应单据页签可修改单号前缀与规则。</li>
          <li><b>换主题？</b>系统设置 → 全局配置 → 界面主题。</li>
        </ul>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const TABS = [
  { key: 'icons', label: '图标详解' },
  { key: 'intro', label: '软件简介' },
  { key: 'map', label: '功能导图' },
  { key: 'start', label: '快速上手' },
  { key: 'modules', label: '模块说明' },
  { key: 'safe', label: '数据与安全' },
]
const tab = ref('icons')

/* 主页四排图标逐一详解（与主页图标一一对应） */
const ICON_GROUPS = [
  { name: '单据排 —— 每天进出的凭证（货动一下，就记一笔）', items: [
    { ic: '📥', n: '入库单', one: '货物进仓库，记这张单。',
      d: '<b>什么时候用：</b>采购到货、别人退货退回来、生产完工入库——凡是货物"进仓库"，都记入库单。<br><b>怎么用：</b>先选日期、往来单位（哪家供应商发的货）、入到哪个仓库、业务类别（"进出类别"里建好的入库类别）——<b>点表头的"往来单位/类别/仓库"框，会弹出对应资料窗口</b>（左侧分类树 + 右侧列表，可现场添加/编辑后再选取，与原版一致）；<b>点底部"供货人/经办人/审核人"框，弹出「工作人员」窗口</b>（左侧人员分类 + 右侧列表选取）；再一行一行填：表格里<b>双击"编码"格弹出「货物资料」窗口</b>（左侧分类树 + 搜索 + 选取，可连续选货），也可以<b>直接输入货物编码</b>回车带出；<b>双击"库位"格弹出「库区库位」窗口</b>（入库/出库/调拨/盘点/期初单据都一样），也可以直接输入库位名称；编码/库位列白底、聚焦绿框，表头停一下有原版同款黄色提示（编码/库位/单价都有），然后填数量和单价（单价默认带出货物资料里的参考价，可改），金额自动=数量×单价，保存即可。<br><b>保存后：</b>库存立刻增加，成本按"移动加权平均法"自动算好，不用手工算；点"打印"可出纸质单据。' },
    { ic: '📤', n: '出库单', one: '货物出仓库，记这张单。',
      d: '<b>什么时候用：</b>销售发货、车间领用、借给别人拿走——货物"出仓库"都记出库单。<br><b>怎么用：</b>填法与入库单一样（选日期、客户、出库仓库、类别，再选货物填数量）。<br><b>保存后：</b>库存立刻减少；出库成本不用填，系统按该货物的加权平均成本自动带出。库存不够时系统会提醒，避免超卖。' },
    { ic: '🔁', n: '调拨单', one: '货没少，只是换了地方。',
      d: '<b>什么时候用：</b>同一批货从A仓库（或A库位）搬到B仓库（或B库位），货没进也没出。<br><b>怎么用：</b>选好"调出仓库+库位"和"调入仓库+库位"，填货物和数量。<br><b>保存后：</b>总库存不变，但两个仓库/库位的数量一减一增，分仓看账都是准的。' },
    { ic: '✅', n: '盘点单', one: '数一数实物，把账对平。',
      d: '<b>什么时候用：</b>定期（建议每月或每季）到仓库清点实物，跟"库存表"里的账面数对比。<br><b>怎么用：</b>新建盘点单选仓库后，账面数量自动带出，填上你实际数出来的"实盘数量"，系统自动算出盈亏数量和金额。<br><b>保存后：</b>库存直接调整为实盘数，盈亏有记录可查。' },
    { ic: '🔍', n: '单据查询', one: '所有历史单据都在这，可查、可改、可删。',
      d: '想找以前开的任何一张入库/出库/调拨/盘点单，在这里按日期、类型、单号、关键字搜索，查到后可查看明细、修改重存或删除。<br><span class="warn">注意：修改或删除旧单据后，相关库存和报表会自动重算，改动前请确认。</span>' },
  ]},
  { name: '报表排 —— 自动算好的账（录了单据，这里全是现成的）', items: [
    { ic: '📦', n: '库存表', one: '现在每样货还剩多少、放在哪。',
      d: '按"货物+仓库"显示实时数量和成本金额，是库存的总账。录完任何单据，这里立刻是最新的。数量低于最低库存（可能缺货）或高于最高库存（可能积压）时，报警列显示"低/高"；点<b>查询</b>弹「库存查询」窗口：分类、货物、仓库、过滤零库存、显示汇总（表格底部合计行）、显示分仓——点<b>货物/仓库</b>框弹对应资料窗口选取（与原版一致），点字段上的 ✕ 可清空。报表只读，最低/最高库存、备注请到「货物资料」里修改。' },
    { ic: '📊', n: '进销存', one: '一段时间的进、出、存总账。',
      d: '选好起止日期后，每个货物一行：期初多少 → 期间进了多少 → 出了多少 → 结存多少，数量和成本金额都分开列。<b>月末对账、看月度经营情况</b>就用它。' },
    { ic: '⇅', n: '进出汇总', one: '看哪些货进出最频繁。',
      d: '把所选期间所有入库、出库按货物汇总成一张表，各货物的进出总量与金额一目了然，方便分析主力货物。' },
    { ic: '📋', n: '进出明细', one: '一笔一笔的流水账。',
      d: '按时间顺序列出每一次进出流水：哪天、什么单据、什么货物、数量、单价、金额、经手人。想核对"某天到底发生了什么"就看这里。点<b>查询</b>弹条件窗口：单据类型、进出类别、货物分类/指定货物、往来单位、进出仓库、供领/经办人员、起止时间，及 汇总结存/分仓结存/均价成本/库位结存 四个显示开关；点<b>货物/仓库/往来单位/进出类别/人员</b>框弹对应资料窗口选取，点<b>开始/结束时间</b>弹「日期时间」窗口（年月切换＋日历＋时/分＋此时/确定，与原版一致）。' },
    { ic: '🥧', n: '利润分析', one: '这段时间毛利赚了多少。',
      d: '统计所选期间每样货物的出货收入、出货成本和毛利润（收入−成本），按货物排列。出库成本是系统自动核算的，所以毛利不用手工算。' },
    { ic: '🧾', n: '借还统计', one: '谁借了货、还了没有。',
      d: '汇总每笔借出/借入：借了多少、已归还多少、还欠多少（待还），以及对应成本金额。借出去的东西心里有数，不会忘。' },
    { ic: '🧮', n: '产品查询', one: '给定型号和数量，看库存配件够不够。',
      d: '在报表排末尾。页面顶部为原版同款<b>操作栏</b>：<b>&lt;主页</b>（返回主页）、<b>查询</b>（按所选型号与数量查库存）、<b>清空</b>（重置条件与结果）、<b>预览 / 打印</b>（打印查询结果）、<b>导出</b>（CSV）。<br>选择要生产的 <b>电机型号</b>（已建好的 BOM），填<b>生产数量</b>，点"查询库存是否足够"。<br><b>结果：</b>逐条列出 BOM 明细——单台用量、<b>需求数量</b>（用量×生产数）、<b>当前库存</b>、<b>缺口</b>，并标 ✔足够 / ✘不足 / ✘未匹配（红行高亮，未匹配表示货物资料里没有该图号/名称的配件，需先录入）。明细按 <b>图号→货物编码 → 名称</b> 自动匹配库存。<br><b>汇总：</b>配件项数、缺料项数、<b>✅ 库存充足可生产 / ❌ 缺料不能生产</b>。' },
  ]},
  { name: '资料排 —— 先建档案（地基：不建好，单据里就没得选）', items: [
    { ic: '📜', n: '货物资料', one: '给每样货物建"身份证"。',
      d: '登记货物的编码（留空自动编）、名称、规格、型号、单位、所属货物分类、<b>默认库位</b>和价格。录单据时选货物就是从这里选。<br><b>窗口结构：</b>左侧货物分类树（工具条按钮管理分类），底部"添加"按钮添加货物。<br><b>默认库位：</b>点该框会弹出"库区库位"选择窗（左侧库位分类树 + 右侧库位表格），双击或选"选取"回填。<br><b>批量导入：</b>点"导入"弹出表格窗口，和原版一样从 Excel 复制后 <b>Ctrl+V 粘贴</b>（列头一致：编码/名称/规格/型号/单位/分类/最低最高库存/四种单价/启用/备注，外加"期初仓库1/2/3"三组仓库+库位+数量+单价+金额），点"检查"再"导入"，可同时建货物并铺期初库存到多个仓库。' },
    { ic: '🏠', n: '期初库存', one: '开始用软件前，把现有家底录进去。',
      d: '第一次使用（或重新建账）时，把仓库里现有的每种货的数量、单价录进来，作为起始库存。以后全靠单据自动增减，不需要再动期初。<br><b>添加期初：</b>点"添加"后，<b>货物 / 仓库 / 库位</b>三个框都和原版一样点击弹出对应资料的选取窗（分类树 + 表格 + 选取），可在弹窗里直接新建再选取；换选仓库会自动清空已选库位。<br><b>工具条：</b>期初明细表右上角三个方形图标按钮：⊞ 添加一行、🗑 删除选中行、✏ 编辑（聚焦选中行首格改数）。' },
    { ic: '🏭', n: '仓库信息', one: '登记你有几个仓库。',
      d: '建立仓库档案（如主仓库、分仓A），可设默认仓库。<b>至少建一个仓库</b>，才能录期初库存和各种单据。' },
    { ic: '🏢', n: '库区库位', one: '仓库里面的具体位置。',
      d: '登记仓库内的货架/货位（如 KW01 默认库位），可挂到某个仓库。货物存放在哪个库位、调拨单从哪搬到哪，都靠它。<br><b>所有仓库：</b>窗口底部"所有仓库"框点一下会弹出"仓库信息"选取窗，选定后右侧库位表只显示该仓库的库位。<br><b>添加库位：</b>表单含 编码/名称/仓库/分类/默认/备注；点"仓库""分类"弹选取窗，点"默认"弹"选择数据"小窗（无/全部/新货物/智能库位）。' },
    { ic: '🔀', n: '进出类别', one: '给每笔进出业务打"标签"。',
      d: '如采购入库、销售出库等业务性质分类，录单据时要选一个，报表就能按业务性质统计。<br><b>窗口结构：</b>左侧"类别分类"树是分类节点（工具条＋🗑✏管理）；右侧表格是类别记录（底部"添加"按钮，编码留空自动编，默认/增减成本/进销统计等下拉与原版一致）。' },
    { ic: '🤝', n: '往来单位', one: '跟你做生意的对方档案。',
      d: '供应商（你从谁那买货）和客户（你把货卖给谁），登记编码、名称、联系人、电话、地址、默认单据类型等。入库单选供应商、出库单选客户，都从这里选。' },
    { ic: '🙂', n: '工作人员', one: '经手这件事的人。',
      d: '登记员工姓名、<b>职务</b>、电话、所属单位等。单据上的经办人、盘点人等都从这里选。<br><b>职务：</b>点"职务"框弹出原版同款"选择数据"小窗，左侧职务列表（双击选中）、右侧按钮 ✔确定 / ↩清空 / ➕添加 / 🗑删除 / ✏编辑；已预置 经理、主管、业务员、仓管员、财务、审核人，可自行增删改。' },
    { ic: '🧩', n: 'BOM', one: '产品的物料清单（装配明细）。',
      d: '在资料排末尾，点开为<b>正方形窗口</b>的 <b>BOM 表管理</b>：列出所有产品的字段内容与零件数，顶部搜索型号或名称。<br><b>自定义字段/列：</b>表头字段（型号/名称/电压/电流/编号/备注）与明细列（数量/图号/名称/基型/备注）都<b>不是写死的</b>——<b>双击字段名或列名</b>可改成自己的名字；点表头 <b>➕ 字段</b>、明细表 <b>➕ 列</b> 可增加新项目（自定义项旁有 ✕ 可删除）；新建 BOM 会自动沿用上一次的定义。<br><b>新建 BOM：</b>填型号（必填）、其余字段按需，下方明细表可逐格编辑（支持"加一行""删除选中行"、<b>从 Excel 直接 Ctrl+V 粘贴</b>，粘贴按当前列的顺序逐列落位）。<br><b>查看 / 编辑 / 删除</b>每行均有；查看弹详情（按自定义字段与列显示）；支持<b>导出 Excel</b>（单个 BOM 明细或全部清单，CSV，列随定义导出）。<br><b>用途：</b>为"产品查询"提供型号与配件清单。BOM 资料也纳入"系统初始化"的清空范围（勾"BOM 资料"）。' },
  ]},
  { name: '系统排 —— 管好软件和数据（设一次、常备份）', items: [
    { ic: '⚙', n: '系统设置', one: '软件的全局开关和参数。',
      d: '公司名称、界面主题（白/绿/蓝青三种颜色）、金额数量的小数位、四种单据的单号前缀与规则、货物自定义字段、成本核算方式等。一般设置一次后不常改动。' },
    { ic: '🔧', n: '个人设置', one: '改自己的资料和密码。',
      d: '当前登录的人修改自己的姓名、职务和登录密码，只影响自己，不影响别人。' },
    { ic: '👥', n: '账号权限', one: '给每个员工开账号、定权限。',
      d: '管理员在这里添加员工账号、重置密码、启用/禁用账号，并按 17 项功能逐项勾选操作权限——<b>没勾的功能，该账号登录后看不到</b>，防止误操作。改动即时生效。' },
    { ic: '💾', n: '备份', one: '把整个数据库下载保存。',
      d: '选择电脑上的保存位置，把当前全部数据存成一个数据库文件。<b>强烈建议每天或每周备份一次</b>，存到U盘或非系统盘，有备无患。' },
    { ic: '♻', n: '还原', one: '用备份文件把数据恢复回去。',
      d: '电脑故障、误操作把数据弄乱时，选一个备份文件即可整体恢复到备份那一刻的状态。<span class="warn">注意：还原会覆盖当前全部数据，操作前务必想清楚。</span>' },
    { ic: '🗑', n: '初始化', one: '清空数据，重新开始。',
      d: '可以只清业务单据（基础资料保留），也可以勾选基础资料连全部资料一起清（用户账号保留）。<span class="warn">清空后不可恢复，初始化前一定先"备份"。</span>' },
    { ic: '📄', n: '操作日志', one: '谁在什么时候动了什么，全有记录。',
      d: '登录、资料增删改、单据保存删除、设置修改、备份还原初始化……所有操作都自动记录在服务器（时间、账号、模块、操作、详情），支持按日期/账号/关键字检索，出问题随时追查。' },
    { ic: '📖', n: '使用说明', one: '就是本页面。',
      d: '图标详解、软件简介、功能导图、快速上手、模块说明、数据与安全都在这里，遇到不会的地方随时打开查。' },
  ]},
]

const MAP = [
  { name: '单据', color: 'var(--ku-accent)', items: [
    { ic: '📥', n: '入库单', tip: '采购入库，库存增加' },
    { ic: '📤', n: '出库单', tip: '销售/领用出库' },
    { ic: '🔁', n: '调拨单', tip: '仓库/库位间转移' },
    { ic: '✅', n: '盘点单', tip: '账实核对，自动调差' },
    { ic: '🔍', n: '单据查询', tip: '查改删历史单据' },
  ]},
  { name: '报表', color: '#2f8f5e', items: [
    { ic: '📦', n: '库存表', tip: '实时库存与报警' },
    { ic: '📊', n: '进销存', tip: '期初/进/出/结存' },
    { ic: '⇅', n: '进出汇总', tip: '按货物汇总进出' },
    { ic: '📋', n: '进出明细', tip: '每笔流水明细' },
    { ic: '🥧', n: '利润分析', tip: '毛利统计' },
    { ic: '🧾', n: '借还统计', tip: '借出借入待还' },
    { ic: '🧮', n: '产品查询', tip: '查库存是否够生产' },
  ]},
  { name: '资料', color: '#b8860b', items: [
    { ic: '📜', n: '货物资料', tip: '编码/规格/价格' },
    { ic: '🗂', n: '货物分类', tip: '货物分类树' },
    { ic: '🏠', n: '期初库存', tip: '建账期初数据' },
    { ic: '🏭', n: '仓库信息', tip: '仓库档案' },
    { ic: '🏢', n: '库区库位', tip: '库位档案' },
    { ic: '🔀', n: '进出类别', tip: '收支类别' },
    { ic: '🤝', n: '往来单位', tip: '供应商/客户' },
    { ic: '🙂', n: '工作人员', tip: '经办人档案' },
    { ic: '🧩', n: 'BOM', tip: '产品物料清单' },
  ]},
  { name: '系统', color: '#7a5fa0', items: [
    { ic: '⚙', n: '系统设置', tip: '主题/字段/单号' },
    { ic: '🔧', n: '个人设置', tip: '改自己的资料密码' },
    { ic: '👥', n: '账号权限', tip: '账号与操作权限' },
    { ic: '💾', n: '备份', tip: '下载数据库' },
    { ic: '♻', n: '还原', tip: '从备份恢复' },
    { ic: '🗑', n: '初始化', tip: '清空数据重建' },
    { ic: '📄', n: '操作日志', tip: '服务器操作记录' },
  ]},
]

/* SVG 里颜色不能用 CSS 变量（presentation attribute 不解析 var），这里取一次主题色实际值 */
const accent = ref(
  (typeof getComputedStyle === 'function' && getComputedStyle(document.documentElement).getPropertyValue('--ku-accent').trim()) || '#2e8ba0'
)

/* ───── 思维导图布局（自算坐标 + 贝塞尔曲线，不引第三方库） ───── */
const MM = {
  W: 1470,            // 画布宽（含右侧说明子节点）
  PAD: 24,            // 上下留白
  BRANCH_GAP: 60,     // 同侧两条主分支之间的间距
  ROW_H: 30,          // 每个功能节点的行高（节点 26 + 间距 4）
  ROOT_W: 170, ROOT_H: 54,
  BRANCH_W: 88, BRANCH_H: 34,
  LEAF_W: 190, TIP_W: 170,
  TIP_LINE: '#a9cdd9', // 功能 → 说明 的细连线
  LEFT_LEAF_X: 292, LEFT_TIP_X: 102, LEFT_BRANCH_X: 380,
  RIGHT_LEAF_X: 1088, RIGHT_TIP_X: 1278, RIGHT_BRANCH_X: 932,
}
// 按字数估算文本高度（CJK 按 1 字宽 1em 计）
function mmTextH(text, fontPx, contentW) {
  const perLine = Math.max(1, Math.floor(contentW / fontPx))
  const lines = Math.max(1, Math.ceil(String(text || '').length / perLine))
  return Math.round(lines * fontPx * 1.45)
}
function mmR(v) { return Math.round(v * 10) / 10 }

const mm = computed(() => {
  // 左列：资料(9) + 报表(7)；右列：单据(5) + 系统(7) —— 按叶数平衡左右
  const nameOf = { 单据: 0, 报表: 1, 资料: 2, 系统: 3 }
  const group = (i) => MAP[i]
  const leftIdx = [nameOf['资料'], nameOf['报表']]
  const rightIdx = [nameOf['单据'], nameOf['系统']]

  const buildCol = (idxList, side) => {
    const branches = []
    const leaves = []
    const links = []
    const tipLinks = []
    let height = 0
    idxList.forEach((mi, k) => {
      if (k > 0) height += MM.BRANCH_GAP
      branches.push({ mi, bi: k, blockTop: height, blockH: group(mi).items.length * MM.ROW_H })
      height += group(mi).items.length * MM.ROW_H
    })

    branches.forEach((b) => {
      const g = group(b.mi)
      const color = g.color === 'var(--ku-accent)' ? accent.value : g.color
      const branchX = side === 'l' ? MM.LEFT_BRANCH_X : MM.RIGHT_BRANCH_X
      const leafX = side === 'l' ? MM.LEFT_LEAF_X : MM.RIGHT_LEAF_X
      const tipX = side === 'l' ? MM.LEFT_TIP_X : MM.RIGHT_TIP_X
      b.color = color
      b.y = mmR(b.blockTop + b.blockH / 2 - MM.BRANCH_H / 2)
      b.cy = mmR(b.y + MM.BRANCH_H / 2)
      g.items.forEach((it, j) => {
        const cy = mmR(b.blockTop + j * MM.ROW_H + MM.ROW_H / 2)
        const tipH = Math.max(20, mmTextH(it.tip, 11, MM.TIP_W - 10))
        const leafH = Math.max(26, 21 + tipH + 5)
        // 主分支 → 功能节点 → 说明子节点，全部三次贝塞尔，左右镜像
        if (side === 'l') {
          links.push({ bi: b.bi, d: `M ${branchX} ${b.cy} C ${branchX - 70} ${b.cy}, ${leafX + MM.LEAF_W + 70} ${cy}, ${leafX + MM.LEAF_W} ${cy}`, color })
          tipLinks.push({ bi: b.bi, d: `M ${leafX} ${cy} C ${leafX - 20} ${cy}, ${tipX + MM.TIP_W + 20} ${cy}, ${tipX + MM.TIP_W} ${cy}`, color: MM.TIP_LINE })
        } else {
          links.push({ bi: b.bi, d: `M ${branchX + MM.BRANCH_W} ${b.cy} C ${branchX + MM.BRANCH_W + 70} ${b.cy}, ${leafX - 70} ${cy}, ${leafX} ${cy}`, color })
          tipLinks.push({ bi: b.bi, d: `M ${leafX + MM.LEAF_W} ${cy} C ${leafX + MM.LEAF_W + 20} ${cy}, ${tipX - 20} ${cy}, ${tipX} ${cy}`, color: MM.TIP_LINE })
        }
        leaves.push({
          bi: b.bi, x: leafX, y: mmR(cy - 13), w: MM.LEAF_W, h: mmR(leafH), cy,
          tipY: cy, label: it.n, ic: it.ic, tip: it.tip, color,
        })
      })
    })
    return { height, branches, leaves, links, tipLinks }
  }

  const left = buildCol(leftIdx, 'l')
  const right = buildCol(rightIdx, 'r')
  const H = mmR(Math.max(left.height, right.height) + MM.PAD * 2)
  const rootX = mmR((MM.W - MM.ROOT_W) / 2)
  const rootY = mmR(H / 2 - MM.ROOT_H / 2)
  const rootCY = mmR(H / 2)

  const branches = []
  const trunks = []
  const leaves = []
  const links = []
  const tipLinks = []
  const offsetOf = (col) => mmR((H - col.height) / 2)

  ;[[left, 'l'], [right, 'r']].forEach(([col, side]) => {
    const dy = offsetOf(col)
    col.branches.forEach((b) => {
      const g = group(b.mi)
      const bx = side === 'l' ? MM.LEFT_BRANCH_X : MM.RIGHT_BRANCH_X
      const by = mmR(b.y + dy)
      const bcy = mmR(b.cy + dy)
      branches.push({ x: bx, y: by, w: MM.BRANCH_W, h: MM.BRANCH_H, cy: bcy, name: g.name, color: b.color })
      // 中心主题 → 主分支（三次贝塞尔，左右镜像）
      if (side === 'l') {
        trunks.push({ d: `M ${rootX} ${rootCY} C ${rootX - 60} ${rootCY}, ${bx + MM.BRANCH_W + 60} ${bcy}, ${bx + MM.BRANCH_W} ${bcy}`, color: b.color })
      } else {
        trunks.push({ d: `M ${rootX + MM.ROOT_W} ${rootCY} C ${rootX + MM.ROOT_W + 60} ${rootCY}, ${bx - 60} ${bcy}, ${bx} ${bcy}`, color: b.color })
      }
      col.leaves.filter(l => l.bi === b.bi).forEach((l) => {
        leaves.push({ ...l, y: mmR(l.y + dy), cy: mmR(l.cy + dy) })
      })
      col.links.filter(l => l.bi === b.bi).forEach((l) => {
        links.push({ d: shiftD(l.d, dy), color: l.color })
      })
      col.tipLinks.filter(l => l.bi === b.bi).forEach((l) => {
        tipLinks.push({ d: shiftD(l.d, dy), color: l.color })
      })
    })
  })

  return {
    viewBox: `0 0 ${MM.W} ${H}`,
    root: { x: rootX, y: rootY, w: MM.ROOT_W, h: MM.ROOT_H },
    branches, leaves, trunks, links, tipLinks,
  }
})

// 把路径里的 y 坐标整体下移 dy（列垂直居中用）
function shiftD(d, dy) {
  return d.replace(/(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)/g, (m, a, b) => `${a} ${mmR(Number(b) + dy)}`)
}

const STEPS = [
  { t: '录基础资料', d: '资料排：货物资料、仓库、库位、往来单位、进出类别、工作人员。也可用 数据管理 → 批量导入（CSV）。' },
  { t: '建期初库存', d: '资料 → 期初库存：录入各货物在仓库/库位的期初数量与单价。' },
  { t: '设置系统参数', d: '系统 → 系统设置：公司名称、界面主题、小数位、单号规则、货物字段等。' },
  { t: '建员工账号', d: '系统 → 账号权限：添加账号并勾选操作权限。' },
  { t: '开始进出存', d: '录入库单/出库单/调拨单/盘点单，库存与报表实时更新。' },
]

const MODULES = [
  { t: '入库单 / 出库单', d: '必选日期、往来单位、仓库、进出类别；每行选货物、库位、数量、单价，金额自动=数量×单价，底部自动合计与大写金额；支持打印。保存后即时影响库存，出库成本按移动加权平均自动核算。' },
  { t: '调拨单', d: '选择调出仓库+库位与调入仓库+库位，两行记账（调拨出/调拨入），总库存不变、分仓库存即时变化。' },
  { t: '盘点单', d: '录入账面数量与实盘数量，系统自动算盈亏数量与金额，保存后库存调整为实盘数。' },
  { t: '库存表', d: '按货物+仓库显示实时数量与成本，报表只读；查询窗口支持 分类/货物/仓库 过滤、过滤零库存、显示汇总合计行、显示分仓；低于最低或高于最高库存时报警列显示 低/高。' },
  { t: '进销存', d: '按期间汇总每个货物的期初、进货、出货、结存的数量与成本，四段双级表头。' },
  { t: '进出明细', d: '逐笔列出所有单据流水（方向、单价、金额、均价、成本、经手人等），查询窗口支持 单据类型/进出类别/货物/仓库/人员/时间 过滤与 汇总结存、分仓结存、均价成本、库位结存 显示开关，只读查询。' },
  { t: '利润分析', d: '按货物统计期间出货收入、成本与毛利润。' },
  { t: '借还统计', d: '借出/借入、归还、待还数量与成本汇总。' },
  { t: '账号权限', d: '账号列表 + 编辑账号（姓名/职务/启用/备注）+ 操作权限树（17 项功能逐项勾选），权限即时生效。' },
  { t: '操作日志', d: '服务器端记录所有数据操作：登录、资料增删改、单据保存删除、设置修改、备份还原初始化等，支持按日期/账号/关键字检索。' },
  { t: 'BOM 管理', d: '资料排 → BOM（🧩）：BOM 表管理。表头字段与明细列均可自定义——双击字段名/列名改名，➕ 字段 / ➕ 列增加项目，自定义项可 ✕ 删除；支持新建、查看、编辑、删除、明细 Excel 粘贴导入（按当前列顺序落位）、导出 CSV。明细为"产品查询"提供型号与配件清单。' },
  { t: '产品查询', d: '报表排 → 产品查询（🧮）：选 BOM 型号 + 生产数量，一键查询每款配件需求数量与当前库存、缺口，按图号→编码→名称自动匹配，汇总"库存是否充足可生产"，支持导出。未匹配配件提示先录入货物资料。' },
]
</script>

<style scoped>
.help-wrap { font-family: "Microsoft YaHei", sans-serif; }
.help-tabs { display: flex; gap: 6px; border-bottom: 2px solid var(--ku-accent); padding: 0 4px; }
.htab { padding: 8px 18px; font-size: 14px; color: var(--ku-text-soft); cursor: pointer; border: 1px solid var(--ku-border-soft); border-bottom: none; background: var(--ku-panel-2); border-radius: 6px 6px 0 0; }
.htab.active { background: var(--ku-accent); color: #fff; font-weight: 600; }
.help-body { padding: 14px 18px; max-height: 62vh; overflow: auto; background: var(--ku-panel-soft); border: 1px solid var(--ku-border-soft); border-top: none; }
.help-body h3 { color: var(--ku-text-soft); margin: 14px 0 8px; font-size: 15px; border-left: 4px solid var(--ku-accent); padding-left: 8px; }
.help-body h3:first-child { margin-top: 0; }
.help-body p, .help-body li { font-size: 14px; color: #333; line-height: 1.9; }
.help-body ul { margin: 4px 0 10px 20px; padding: 0; }
.warn { color: #b26a00; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; vertical-align: middle; }
.dot.g { background: #3ad07a; } .dot.y { background: #ffd04b; } .dot.r { background: #ff5252; }

/* 图标详解卡片 */
.ic-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 8px; }
.ic-card { display: flex; gap: 10px; background: var(--ku-panel-2); border: 1px solid var(--ku-border-soft); border-radius: 8px; padding: 10px 12px; }
.ic-side { flex: 0 0 64px; text-align: center; }
.ic-emoji { font-size: 30px; line-height: 1.2; display: block; }
.ic-name { font-size: 13px; font-weight: 700; color: var(--ku-text-soft); display: block; margin-top: 2px; }
.ic-txt { flex: 1; font-size: 13px; color: #333; line-height: 1.85; }
.ic-txt span { display: block; }
.ic-one { color: var(--ku-accent); display: block; margin-bottom: 2px; }
@media (max-width: 1000px) { .ic-grid { grid-template-columns: 1fr; } }

/* 思维导图（SVG 手绘：中心主题 + 左右辐射分支 + 贝塞尔曲线） */
.mindmap { background: var(--ku-panel-2); border: 1px solid var(--ku-border-soft); border-radius: 8px; padding: 16px; overflow-x: auto; }
.mm-svg { width: 100%; min-width: 1150px; height: auto; display: block; }
.mm-svg path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
.mm-root-box { fill: #fff; stroke: var(--ku-accent); stroke-width: 3; }
.mm-root-name { font-size: 18px; font-weight: 700; text-anchor: middle; fill: var(--ku-accent); letter-spacing: 1px; }
.mm-branch-box { filter: drop-shadow(0 2px 4px rgba(0,0,0,.18)); }
.mm-branch-name { font-size: 15px; font-weight: 700; text-anchor: middle; letter-spacing: 3px; }
.mm-leaf-box { fill: #fff; stroke-width: 1.5; opacity: .98; }
.mm-leaf-name { font-size: 13px; font-weight: 600; fill: var(--ku-text); }
.mm-leaf-ic { font-size: 13px; }
.mm-fo { overflow: visible; }
.mm-leaf-tip { font-size: 11px; line-height: 1.35; color: var(--ku-muted); padding: 2px 0 0; }

/* 步骤 */
.steps { display: flex; flex-direction: column; gap: 10px; margin: 8px 0 14px; }
.step { display: flex; align-items: flex-start; gap: 12px; }
.step-no { flex: 0 0 26px; height: 26px; border-radius: 50%; background: var(--ku-accent); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; }
.step-txt { font-size: 14px; color: #333; line-height: 1.7; }
.step-txt span { color: #555; }
.mod { margin-bottom: 12px; border-bottom: 1px dashed var(--ku-border-soft); padding-bottom: 10px; }
.mod-t { font-weight: 700; color: var(--ku-text-soft); font-size: 14px; margin-bottom: 3px; }
.mod-d { font-size: 13px; color: #444; line-height: 1.8; }
</style>
