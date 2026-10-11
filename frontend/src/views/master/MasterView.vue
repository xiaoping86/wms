<template>
  <div class="ku-win">
    <div class="ku-win-body">
      <!-- 左侧分类列（原版：工具条小按钮 + 分类列表） -->
      <div class="ku-side no-print">
        <div class="ku-side-tools">
          <div class="ku-icon-btn" title="添加分类" @click="openCatAdd">
            <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="#111" stroke-width="2"/><path d="M12 7.5v9M7.5 12h9" stroke="#111" stroke-width="2"/></svg>
          </div>
          <div class="ku-icon-btn" title="删除分类" @click="removeCatBtn">
            <svg viewBox="0 0 24 24"><path d="M4 6.5h16M9.5 6.5V4.8a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v1.7M6 6.5l1 13.5h10l1-13.5M9.7 10v7M14.3 10v7" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="ku-icon-btn" title="编辑分类" @click="editCatBtn">
            <svg viewBox="0 0 24 24"><path d="M3.5 20.5l1.3-4.8L15.5 5a2.3 2.3 0 0 1 3.2 3.2L8 18.9l-4.5 1.6z" fill="none" stroke="#111" stroke-width="2" stroke-linejoin="round"/></svg>
          </div>
          <div class="ku-icon-btn" title="上移" @click="moveRow(-1)">
            <svg viewBox="0 0 24 24"><path d="M12 20.5V4.5M4.8 11.2 12 4l7.2 7.2" fill="none" stroke="#111" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="ku-icon-btn" title="下移" @click="moveRow(1)">
            <svg viewBox="0 0 24 24"><path d="M12 3.5v16M4.8 12.8 12 20l7.2-7.2" fill="none" stroke="#111" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
        </div>
        <div class="ku-tree">
          <div class="tree-list">
            <div class="node root" :class="{ sel: treeSel === 'ROOT' }">
              <span class="tv-box" :class="{ open: !catCollapsed }" @click.stop="catCollapsed = !catCollapsed"></span>
              <span class="tv-label" @click="treeSel = 'ROOT'">{{ cfg.treeLabel }}</span>
            </div>
            <template v-if="!catCollapsed">
              <div v-for="n in treeNodes" :key="n.id" class="node child" :class="{ sel: treeSel === n.id, first: n.first }"
                   :style="'padding-left:' + (24 + n.depth * 14) + 'px;--lx:' + (13 + n.depth * 14) + 'px'"
                   @click="onCatClick(n)">
                <span v-if="n.hasKids" class="tv-box" :class="{ open: !collapsedCats.has(n.id) }" @click.stop="toggleCat(n.id)"></span>
                <span v-else class="tv-box leaf"></span>
                <span class="tv-label">{{ n.name }}</span>
              </div>
            </template>
          </div>
        <!-- 原版左侧分类列底部无 ➕（➕ 在上方工具条），此处不再显示 -->
        </div>
      </div>
      <!-- 右侧表格 -->
      <div class="ku-win-main">
        <div class="scroll">
          <table class="ku-grid" :data-grid-key="'master.' + entity">
            <thead>
              <tr><th v-for="c in cfg.cols" :key="c.key" :style="c.w ? 'width:'+c.w : ''">{{ c.label }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in paged" :key="r.id" :class="{ sel: selId === r.id }" @click="selId = r.id" @dblclick="pickMode ? doPick(r) : editSelected(r)">
                <td v-for="c in cfg.cols" :key="c.key" :class="{ num: c.num }">{{ disp(r, c) }}</td>
              </tr>
              <tr v-if="!paged.length" class="ku-empty-row"><td :colspan="cfg.cols.length"></td></tr>
            </tbody>
          </table>
        </div>
        <div class="ku-win-foot">
          <span>每页{{ pageSize }}行</span>
          <span class="pg">
            第{{ page }}页 / 共{{ totalPages }}页
            <a @click="page = 1">首页</a><a @click="page = Math.max(1, page - 1)">上页</a>
            <a @click="page = Math.min(totalPages, page + 1)">下页</a><a @click="page = totalPages">尾页</a>
          </span>
        </div>
      </div>
    </div>
    <!-- 底部搜索 + 按钮（原版：模糊搜索 / 查询 / 清空 + 导入 添加 删除 编辑） -->
    <div class="ku-actions no-print">
      <template v-if="cfg.isInitial">
        <el-select v-model="whFilter" clearable placeholder="所有仓库" style="width:130px" size="small">
          <el-option v-for="w in (options.warehouses || [])" :key="w.id" :label="w.name" :value="w.id" />
        </el-select>
      </template>
      <!-- 原版行为：库区库位点「所有仓库」弹出仓库信息选取窗 -->
      <a v-else-if="entity === 'locations'" class="wh-pick" title="点击选择仓库" @click="openWhPick">
        <span class="wh-pick-val" :class="{ ph: !whFilter }">{{ whFilter ? (options.warehouses || []).find(w => w.id === whFilter)?.name || '所有仓库' : '所有仓库' }}</span>
        <span class="wh-pick-ico">▼</span>
      </a>
      <input class="ku-input" v-model="kw" placeholder="模糊搜索" @keyup.enter="page = 1" />
      <button class="ku-btn sq" title="查询" @click="page = 1">🔍</button>
      <button class="ku-btn sq" title="清空" @click="kw = ''">✕</button>
      <button class="ku-btn" v-if="cfg.canImport" @click="importVisible = true">导入</button>
      <button class="ku-btn" @click="openAddRecord">添加</button>
      <button class="ku-btn" @click="removeSelected()">删除</button>
      <button class="ku-btn" @click="editSelected()">编辑</button>
      <button class="ku-btn" v-if="pickMode" @click="doPick()">选 取</button>
    </div>

    <!-- 拾取模式：通用选取窗口（原版：人员→所属单位弹往来单位；货物→默认库位弹库区库位；期初→货物/仓库/库位分别弹对应资料窗口） -->
    <el-dialog draggable overflow v-model="winPickOn" :title="PICK_TITLES[winPickEntity] || '选择数据'" width="1000px" append-to-body class="win-dlg unit-pick-dlg">
      <div class="unit-pick-body">
        <MasterView :entity="winPickEntity" pick-mode @pick="onUnitPicked" />
      </div>
    </el-dialog>

    <!-- 添加/编辑（原版两列布局） -->
    <el-dialog draggable overflow class="win-dlg" v-model="visible" :title="dlgTitle" width="680px" append-to-body>
      <el-form :model="form" label-width="90px" class="fg2">
        <el-form-item v-for="fld in cfg.fields" :key="fld.key" :label="fld.label" :required="fld.required" :class="{ full: fld.full }">
          <div v-if="fld.ref && isCatRef(fld)" class="pick-field" @click="openPicker(fld)">
            <span class="pick-val" :class="{ ph: !form[fld.key] }">{{ refName(fld) }}</span>
            <span class="pick-ico">▦</span>
          </div>
          <!-- 原版行为：点"所属单位"打开往来单位窗口选取 -->
          <div v-else-if="fld.pickWin" class="pick-field" @click="openWinPick(fld)">
            <span class="pick-val" :class="{ ph: !form[fld.key] }">{{ refName(fld) }}</span>
            <span class="pick-ico">▦</span>
          </div>
          <!-- 原版行为：点"职务"弹出"选择数据"小窗（可添加/删除/编辑职务）；库位"默认"为固定选项 -->
          <div v-else-if="fld.pickData || fld.pickOpts" class="pick-field" @click="openDataPick(fld)">
            <span class="pick-val" :class="{ ph: !form[fld.key] }">{{ form[fld.key] || '点击选择' }}</span>
            <span class="pick-ico">▦</span>
          </div>
          <el-select v-else-if="fld.selOpts" v-model="form[fld.key]" placeholder="请选择" style="width:100%" clearable>
            <el-option v-for="o in fld.selOpts" :key="String(o.id)" :label="o.name" :value="o.id" />
          </el-select>
          <el-select v-else-if="fld.ref" v-model="form[fld.key]" placeholder="请选择" style="width:100%" clearable filterable>
            <el-option v-for="o in optsOf(fld)" :key="o.id" :label="o.name" :value="o.id" />
          </el-select>
          <el-checkbox v-else-if="fld.type === 'bool'" v-model="form[fld.key]" :true-value="1" :false-value="0" />
          <el-input v-else-if="fld.type === 'number'" v-model.number="form[fld.key]" type="number" :placeholder="fld.ph" />
          <el-input v-else v-model="form[fld.key]" :type="fld.textarea ? 'textarea' : ''" :placeholder="fld.ph" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑货物（原版专属窗口） -->
    <el-dialog draggable overflow class="win-dlg dlg-fit" v-model="goodsVisible" :title="editing ? '编辑货物' : '添加货物'" width="660px" append-to-body>
      <el-form :model="form" label-width="90px" class="fg2">
        <el-form-item label="编码"><el-input v-model="form.code" placeholder="留空则自动编码" :disabled="editing && !!form.code" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="规格"><el-input v-model="form.spec" /></el-form-item>
        <el-form-item label="型号"><el-input v-model="form.model" /></el-form-item>
        <el-form-item label="单位">
          <el-select v-model="form.unit" filterable allow-create default-first-option clearable placeholder="" style="width:100%">
            <el-option v-for="u in UNIT_OPTS" :key="u" :label="u" :value="u" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <div class="pick-field" @click="openPicker({ ref: 'goods-categories', key: 'goods_category_id' })">
            <span class="pick-val" :class="{ ph: !form.goods_category_id }">{{ refName({ key: 'goods_category_id', ref: 'goods-categories' }) }}</span>
            <span class="pick-ico">▦</span>
          </div>
        </el-form-item>
        <el-form-item label="最低库存"><el-input v-model.number="form.min_stock" type="number" placeholder="库存报警基准数" /></el-form-item>
        <el-form-item label="最高库存"><el-input v-model.number="form.max_stock" type="number" placeholder="库存报警基准数" /></el-form-item>
        <el-form-item label="入库单价"><el-input v-model.number="form.in_price" type="number" placeholder="供参考，非固定" /></el-form-item>
        <el-form-item label="出库单价"><el-input v-model.number="form.out_price" type="number" placeholder="供参考，非固定" /></el-form-item>
        <el-form-item label="调拨单价"><el-input v-model.number="form.transfer_price" type="number" placeholder="供参考，非固定" /></el-form-item>
        <el-form-item label="盘点单价"><el-input v-model.number="form.chk_price" type="number" placeholder="供参考，非固定" /></el-form-item>
        <!-- 原版货物编辑窗口无"默认库位"字段 -->
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
        <el-form-item label="启用" class="full"><el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" style="--el-switch-on-color: var(--ku-accent)" /></el-form-item>
      </el-form>
      <div v-if="!editing" class="qc-box">
        <div class="qc-head">
          <b>期初库存：</b>
          <span style="flex:1"></span>
          <div class="qc-tools">
            <a class="qc-ico-btn" title="添加行" @click="qcAdd">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3.5" y="3.5" width="17" height="17" rx="1.5"/><path d="M12 7.5v9M7.5 12h9"/></svg>
            </a>
            <a class="qc-ico-btn" title="删除选中行" @click="qcDel">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6.5h16M9.5 4h5M6.5 6.5L7.5 21h9l1-14.5M10 10.5v6.5M14 10.5v6.5"/></svg>
            </a>
            <a class="qc-ico-btn" title="编辑选中行" @click="qcEdit">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20l4.5-1L20 7.5 16.5 4 5 15.5 4 20z"/><path d="M14 6.5L17.5 10"/></svg>
            </a>
          </div>
        </div>
        <table class="ku-grid qc-grid" data-grid-key="master.qc">
          <thead><tr><th style="width:20%">仓库</th><th style="width:20%">库位</th><th>数量</th><th>单价</th><th>金额</th><th style="width:20%">备注</th></tr></thead>
          <tbody>
            <tr v-for="(q, i) in qcRows" :key="i" :class="{ sel: qcSel === i }" @click="qcSel = i">
              <td>
                <select class="qc-input" v-model="q.warehouse_id" @change="q.location_id = null">
                  <option v-for="w in (options.warehouses || [])" :key="w.id" :value="w.id">{{ w.name }}</option>
                </select>
              </td>
              <td>
                <select class="qc-input" v-model="q.location_id">
                  <option v-for="l in locsOfWh(q.warehouse_id)" :key="l.id" :value="l.id">{{ l.name }}</option>
                </select>
              </td>
              <td><input class="qc-input" type="number" v-model.number="q.qty" @input="qcCalc(q)" /></td>
              <td><input class="qc-input" type="number" v-model.number="q.price" @input="qcCalc(q)" /></td>
              <td class="qc-amt">{{ fmtAmt(q.amount) }}</td>
              <td><input class="qc-input" v-model="q.remark" /></td>
            </tr>
            <tr v-if="!qcRows.length" class="ku-empty-row"><td colspan="6"></td></tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="saveGoods">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑期初（原版专属窗口） -->
    <el-dialog draggable overflow class="win-dlg dlg-fit" v-model="initialVisible" :title="editing ? '编辑期初' : '添加期初'" width="620px" append-to-body>
      <el-form :model="form" label-width="70px" class="fg2">
        <el-form-item label="货物" required>
          <div class="pick-field" @click="openWinPick({ key: 'goods_id', pickWin: 'goods' })">
            <span class="pick-val" :class="{ ph: !form.goods_id }">{{ goodsLabel(form.goods_id) }}</span>
            <span class="pick-ico">▦</span>
          </div>
        </el-form-item>
        <el-form-item label="仓库" required>
          <div class="pick-field" @click="openWinPick({ key: 'warehouse_id', pickWin: 'warehouses' })">
            <span class="pick-val" :class="{ ph: !form.warehouse_id }">{{ refName({ key: 'warehouse_id', ref: 'warehouses' }) }}</span>
            <span class="pick-ico">▦</span>
          </div>
        </el-form-item>
        <el-form-item label="库位">
          <div class="pick-field" @click="openWinPick({ key: 'location_id', pickWin: 'locations' })">
            <span class="pick-val" :class="{ ph: !form.location_id }">{{ refName({ key: 'location_id', ref: 'locations' }) }}</span>
            <span class="pick-ico">▦</span>
          </div>
        </el-form-item>
        <el-form-item label="数量" required><el-input v-model.number="form.qty" type="number" @input="calcAmount" /></el-form-item>
        <el-form-item label="单价"><el-input v-model.number="form.price" type="number" @input="calcAmount" /></el-form-item>
        <el-form-item label="金额"><el-input v-model.number="form.amount" type="number" /></el-form-item>
        <el-form-item label="备注" class="full"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="initialVisible = false">取消</el-button>
        <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="saveInitial">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑分类（原版小窗口：编码留空自动编码 / 上级 / 名称 / 备注，仅保存） -->
    <el-dialog draggable overflow class="win-dlg dlg-fit" v-model="catVisible" :title="editing ? '编辑分类' : '添加分类'" width="440px" append-to-body>
      <el-form :model="catForm" label-width="80px">
        <el-form-item label="编码"><el-input v-model="catForm.code" placeholder="留空则自动编码" /></el-form-item>
        <el-form-item label="上级">
          <div class="pick-field" @click="openPicker({ ref: catRef, key: 'parent_id', form: catForm })">
            <span class="pick-val" :class="{ ph: !catForm.parent_id }">{{ parentName(catForm.parent_id) }}</span>
            <span class="pick-ico">▦</span>
          </div>
        </el-form-item>
        <el-form-item label="名称" required><el-input v-model="catForm.name" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="catForm.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <button class="ku-btn" @click="saveCat">保存</button>
      </template>
    </el-dialog>

    <!-- 选择分类（原版：虚线树+展开框，右侧竖排 确定/清空/添加/删除/编辑/上移/下移） -->
    <el-dialog draggable overflow class="win-dlg dlg-fit" v-model="picker.on" title="选择分类" width="340px" append-to-body>
      <div class="pick-wrap">
        <div class="pick-tree pick-tree-dotted">
          <div v-for="n in pickNodes" :key="n.id" class="pick-node" :class="{ sel: selPid === n.id }"
               :style="'padding-left:' + (6 + n.depth * 16) + 'px'" @click="selPid = n.id" @dblclick="pickOk">
            <span v-if="n.hasKids" class="tv-box" :class="{ open: pickExpanded.has(n.id) }" @click.stop="togglePick(n.id)"></span>
            <span v-else class="tv-box leaf"></span>
            <span class="pick-name">{{ n.name }}</span>
          </div>
        </div>
        <div class="pick-btns">
          <a class="pick-btn" title="确定" @click="pickOk">✔</a>
          <a class="pick-btn" title="清空" @click="pickClear">↩</a>
          <a class="pick-btn" title="添加分类" @click="openCat2">➕</a>
          <a class="pick-btn" title="删除分类" @click="pickDel">🗑</a>
          <a class="pick-btn" title="编辑分类" @click="pickEdit">✏</a>
          <a class="pick-btn" title="上移" @click="pickMove(-1)">↑</a>
          <a class="pick-btn" title="下移" @click="pickMove(1)">↓</a>
        </div>
      </div>
    </el-dialog>

    <!-- 选择数据（原版：职务等字典字段小窗，右侧竖排 确定/清空/添加/删除/编辑） -->
    <el-dialog draggable overflow class="win-dlg dlg-fit" v-model="dpk.on" title="选择数据" width="340px" append-to-body>
      <div class="pick-wrap">
        <div class="dpk-list">
          <div v-for="r in dpk.rows" :key="r.id" class="dpk-row" :class="{ sel: dpk.sel === r.id }"
               @click="dpk.sel = r.id" @dblclick="dpkOk">{{ r.name }}</div>
          <div v-if="!dpk.rows.length" class="dpk-empty">{{ dpk.static ? '暂无可选项' : '暂无职务，点右侧 ➕ 添加' }}</div>
        </div>
        <div class="pick-btns">
          <a class="pick-btn" title="确定" @click="dpkOk">✔</a>
          <a class="pick-btn" title="清空" @click="dpkClear">↩</a>
          <a v-if="!dpk.static" class="pick-btn" title="添加职务" @click="dpkAdd">➕</a>
          <a v-if="!dpk.static" class="pick-btn" title="删除职务" @click="dpkDel">🗑</a>
          <a v-if="!dpk.static" class="pick-btn" title="编辑职务" @click="dpkEdit">✏</a>
        </div>
      </div>
    </el-dialog>

    <!-- 添加/编辑职务（从选择数据小窗打开） -->
    <el-dialog draggable overflow class="win-dlg" v-model="dpkFormOn" :title="dpkEditing ? '编辑职务' : '添加职务'" width="380px" append-to-body>
      <el-form :model="dpkForm" label-width="80px">
        <el-form-item label="编码"><el-input v-model="dpkForm.code" placeholder="留空则自动编码" :disabled="dpkEditing && !!dpkForm.code" /></el-form-item>
        <el-form-item label="名称" required><el-input v-model="dpkForm.name" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="dpkForm.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <button class="ku-btn" @click="dpkSave">保存</button>
      </template>
    </el-dialog>

    <!-- 添加/编辑分类（从选择分类中打开；原版仅保存按钮） -->
    <el-dialog draggable overflow class="win-dlg" v-model="cat2On" :title="cat2Editing ? '编辑分类' : '添加分类'" width="420px" append-to-body>
      <el-form :model="catForm2" label-width="80px">
        <el-form-item label="编码"><el-input v-model="catForm2.code" placeholder="留空则自动编码" :disabled="cat2Editing && !!catForm2.code" /></el-form-item>
        <el-form-item label="上级">
          <el-select v-model="catForm2.parent_id" placeholder="（无）" style="width:100%" clearable>
            <el-option v-for="n in pickParentOpts" :key="n.id" :label="n.name" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required><el-input v-model="catForm2.name" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="catForm2.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <button class="ku-btn" @click="saveCat2">保存</button>
      </template>
    </el-dialog>

    <!-- 批量导入（原版行为：点"导入"弹出表格，从 Excel 复制后 Ctrl+V 粘贴，检查后导入） -->
    <el-dialog draggable overflow class="win-dlg" v-model="importVisible" :title="cfg.title + ' · 导入'" width="1080px" append-to-body>
      <div class="imp-wrap" @paste="impPaste">
        <div class="imp-tip">从 Excel 复制若干行，直接在本表格按 <b>Ctrl+V</b> 粘贴；也可逐格输入。列顺序：{{ impCols.map(c => c.label).join('、') }}（多余的列自动忽略）。粘贴后先「检查」再「导入」。</div>
        <div class="imp-scroll">
          <table class="ku-grid imp-grid" data-grid-key="master.imp">
            <thead>
              <tr>
                <th rowspan="2" style="width:120px">提示</th>
                <th v-for="c in impBasic" :key="c.key" rowspan="2" :style="c.w ? 'width:'+c.w : ''">{{ c.label }}</th>
                <th v-for="(g, gi) in impGroups" :key="'g' + gi" :colspan="impQcSub.length" class="grp">{{ g }}</th>
              </tr>
              <tr v-if="impGroups.length">
                <template v-for="(g, gi) in impGroups" :key="'sg' + gi">
                  <th v-for="s in impQcSub" :key="gi + s.key" :style="s.w ? 'width:'+s.w : ''">{{ s.label }}</th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in impRows" :key="i" :class="{ sel: impSel === i, bad: r.tip && r.tip.indexOf('✗') === 0 }" @click="impSel = i">
                <td class="tip">{{ r.tip }}</td>
                <td v-for="c in impCols" :key="c.key"><input class="imp-input" v-model="r[c.key]" @focus="impSel = i" /></td>
              </tr>
              <tr v-if="!impRows.length" class="ku-empty-row"><td :colspan="impCols.length + 1" style="text-align:center;padding:24px;color:#999">在 Excel 中复制数据行，然后按 Ctrl+V 粘贴到这里</td></tr>
            </tbody>
          </table>
        </div>
        <div class="imp-bar">
          <span class="imp-msg" :class="{ bad: impBad }">{{ impMsg }}</span>
          <span style="flex:1"></span>
          <button class="ku-btn" @click="impAddRows(10)">加10行</button>
          <button class="ku-btn" @click="impClear">清空</button>
          <button class="ku-btn" @click="impCheck">检查</button>
          <button class="ku-btn imp-go" @click="impImport">导入</button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

/* 是/否 下拉（原版类别窗口的标记列） */
const YN = [{ id: '否', name: '否' }, { id: '是', name: '是' }]
/* 原版"默认"下拉（往来单位/工作人员：该往来对象默认用于哪种单据） */
const DFT_OPTS = [
  { id: '无', name: '无' }, { id: '全部', name: '全部' }, { id: '入库单', name: '入库单' },
  { id: '出库单', name: '出库单' }, { id: '调拨单', name: '调拨单' }, { id: '盘点单', name: '盘点单' },
]
/* 原版进出类别"增减成本"下拉 */
const CB_OPTS = [{ id: '用标价', name: '用标价' }, { id: '用均价', name: '用均价' }]
/* 原版进出类别"进销统计"下拉 */
const JXTJ_OPTS = [
  { id: '进货正数', name: '进货正数' }, { id: '进货负数', name: '进货负数' },
  { id: '出货正数', name: '出货正数' }, { id: '出货负数', name: '出货负数' },
  { id: '调拨盘点', name: '调拨盘点' },
]

/* 通用添加/编辑弹窗标题（原版：进出类别窗口为"添加类别/编辑类别"） */
const dlgTitle = computed(() => (editing.value ? '编辑' : '添加') + (entity.value === 'categories' ? '类别' : ' ' + cfg.value.title))

/* 显示列（对应原版窗口）+ 编辑表单字段 */
const MASTERS = {
  goods: {
    title: '货物资料', endpoint: 'goods', treeLabel: '货物分类', treeSrc: 'goods-categories', treeField: 'goods_category_id', canImport: true, pageSize: 20,
    cols: [
      { key: 'code', label: '编码', w: '70px' }, { key: 'name', label: '名称', w: '90px' },
      { key: 'spec', label: '规格' }, { key: 'model', label: '型号' }, { key: 'unit', label: '单位', w: '50px' },
      { key: 'stock', label: '全部库存', w: '80px', num: true }, { key: 'cat', label: '分类', w: '90px' },
      { key: 'remark', label: '备注' },
    ],
    fields: [], // 使用原版专属"添加货物"弹窗
  },
  'goods-categories': {
    title: '货物分类', endpoint: 'goods-categories', treeLabel: '货物分类', pageSize: 10,
    cols: [{ key: 'code', label: '编码', w: '90px' }, { key: 'name', label: '名称' }, { key: 'remark', label: '备注' }],
    fields: [{ key: 'code', label: '编码' }, { key: 'name', label: '名称', required: true }, { key: 'parent_id', label: '上级', ref: 'self' }, { key: 'remark', label: '备注' }],
  },
  'unit-categories': {
    title: '单位分类', endpoint: 'unit-categories', treeLabel: '单位分类', pageSize: 10,
    cols: [{ key: 'code', label: '编码', w: '90px' }, { key: 'name', label: '名称' }, { key: 'remark', label: '备注' }],
    fields: [{ key: 'code', label: '编码' }, { key: 'name', label: '名称', required: true }, { key: 'parent_id', label: '上级', ref: 'self' }, { key: 'remark', label: '备注' }],
  },
  'personnel-categories': {
    title: '人员分类', endpoint: 'personnel-categories', treeLabel: '人员分类', pageSize: 10,
    cols: [{ key: 'code', label: '编码', w: '90px' }, { key: 'name', label: '名称' }, { key: 'remark', label: '备注' }],
    fields: [{ key: 'code', label: '编码' }, { key: 'name', label: '名称', required: true }, { key: 'parent_id', label: '上级', ref: 'self' }, { key: 'remark', label: '备注' }],
  },
  categories: {
    title: '进出类别', endpoint: 'categories', treeLabel: '类别分类', treeSrc: 'category-classes', treeField: 'class_id', pageSize: 10,
    cols: [{ key: 'code', label: '编码', w: '80px' }, { key: 'name', label: '名称' }, { key: 'dft', label: '默认', w: '90px' }, { key: 'remark', label: '备注' }],
    // 原版"添加类别"窗口：左列 编码/名称/增减成本/增减利润/重算均价/备注，右列 分类/默认/进销统计/需要归还/扣减待还
    fields: [
      { key: 'code', label: '编码', ph: '留空则自动编码' },
      { key: 'class_id', label: '分类', ref: 'category-classes' },
      { key: 'name', label: '名称', required: true },
      { key: 'sel', label: '默认', selOpts: DFT_OPTS },
      { key: 'zjcb', label: '增减成本', selOpts: CB_OPTS },
      { key: 'jxtj', label: '进销统计', selOpts: JXTJ_OPTS },
      { key: 'zjlr', label: '增减利润', selOpts: YN },
      { key: 'xygh', label: '需要归还', selOpts: YN },
      { key: 'csjj', label: '重算均价', selOpts: YN },
      { key: 'kjdh', label: '扣减待还', selOpts: YN },
      { key: 'remark', label: '备注', full: true },
    ],
  },
  warehouses: {
    title: '仓库信息', endpoint: 'warehouses', treeLabel: '仓库分类', treeSrc: 'warehouse-categories', treeField: 'warehouse_category_id', pageSize: 10,
    cols: [{ key: 'code', label: '编码', w: '90px' }, { key: 'name', label: '名称' }, { key: 'dft', label: '默认', w: '80px' }, { key: 'remark', label: '备注' }],
    fields: [
      { key: 'code', label: '编码', ph: '留空则自动编码' },
      { key: 'warehouse_category_id', label: '分类', ref: 'warehouse-categories', required: true },
      { key: 'name', label: '名称', required: true, full: true },
      { key: 'address', label: '地址', full: true },
      { key: 'contact', label: '联系人' }, { key: 'phone', label: '电话' },
      { key: 'dft', label: '默认', selOpts: DFT_OPTS, required: true },
      { key: 'remark', label: '备注' },
    ],
  },
  locations: {
    title: '库区库位', endpoint: 'locations', treeLabel: '库位分类', treeSrc: 'location-categories', treeField: 'location_category_id', pageSize: 10,
    cols: [
      { key: 'code', label: '编码', w: '80px' }, { key: 'name', label: '名称' },
      { key: 'wh', label: '仓库', w: '90px' }, { key: 'cat', label: '分类', w: '90px' },
      { key: 'dft', label: '默认', w: '80px' }, { key: 'remark', label: '备注' },
    ],
    fields: [
      { key: 'code', label: '编码', ph: '留空则自动编码' },
      { key: 'name', label: '名称', required: true },
      { key: 'warehouse_id', label: '仓库', pickWin: 'warehouses' },
      { key: 'location_category_id', label: '分类', ref: 'location-categories' },
      { key: 'dft', label: '默认', pickOpts: ['无', '全部', '新货物', '智能库位'] },
      { key: 'remark', label: '备注' },
    ],
  },
  units: {
    title: '往来单位', endpoint: 'units', treeLabel: '单位分类', treeSrc: 'unit-categories', treeField: 'unit_category_id', canImport: true, pageSize: 10,
    cols: [
      { key: 'code', label: '编码', w: '80px' }, { key: 'name', label: '名称' }, { key: 'contact', label: '联系人', w: '90px' },
      { key: 'phone', label: '电话', w: '120px' }, { key: 'dft', label: '默认', w: '60px' }, { key: 'remark', label: '备注' },
    ],
    fields: [
      { key: 'code', label: '编码', ph: '留空则自动编码' },
      { key: 'unit_category_id', label: '分类', ref: 'unit-categories' },
      { key: 'name', label: '名称', required: true, full: true },
      { key: 'address', label: '地址', full: true },
      { key: 'contact', label: '联系人' }, { key: 'phone', label: '电话' },
      { key: 'dft', label: '默认', selOpts: DFT_OPTS },
      { key: 'remark', label: '备注' },
    ],
  },
  personnel: {
    title: '工作人员', endpoint: 'personnel', treeLabel: '人员分类', treeSrc: 'personnel-categories', treeField: 'personnel_category_id', pageSize: 10,
    cols: [
      { key: 'code', label: '编码', w: '70px' }, { key: 'name', label: '姓名', w: '90px' },
      { key: 'phone', label: '电话', w: '110px' }, { key: 'prole', label: '职务', w: '90px' },
      { key: 'unit', label: '单位', w: '150px' }, { key: 'dft', label: '默认', w: '50px' }, { key: 'remark', label: '备注' },
    ],
    fields: [
      { key: 'code', label: '编码' }, { key: 'name', label: '姓名', required: true },
      { key: 'phone', label: '电话' }, { key: 'prole', label: '职务', pickData: true },
      { key: 'unit_id', label: '所属单位', ref: 'units', pickWin: true },
      { key: 'personnel_category_id', label: '人员分类', ref: 'personnel-categories' },
      { key: 'dft', label: '默认', selOpts: DFT_OPTS },
      { key: 'remark', label: '备注' },
    ],
  },
  initial: {
    title: '期初库存', endpoint: 'initial-items', treeLabel: '货物分类', isInitial: true, pageSize: 20,
    cols: [
      { key: 'code', label: '编码', w: '70px' }, { key: 'name', label: '名称' }, { key: 'spec', label: '规格' },
      { key: 'model', label: '型号' }, { key: 'unit', label: '单位', w: '50px' }, { key: 'warehouse', label: '仓库', w: '90px' },
      { key: 'location', label: '库位', w: '90px' }, { key: 'qty', label: '数量', num: true },
      { key: 'price', label: '单价', num: true }, { key: 'amount', label: '金额', num: true }, { key: 'remark', label: '备注' },
    ],
    fields: [],
  },
}
const UTYPE = [{ id: 'supplier', name: '供应商' }, { id: 'customer', name: '客户' }, { id: 'both', name: '通用' }]

const props = defineProps({ entity: String, pickMode: { type: Boolean, default: false } })
const emit = defineEmits(['pick'])
const route = useRoute()
const router = useRouter()
const entity = ref(props.entity || route.params.entity)
const cfg = computed(() => MASTERS[entity.value] || MASTERS.goods)

const rows = ref([])
const options = reactive({ utypes: UTYPE })
const visible = ref(false)
const importVisible = ref(false)
const editing = ref(false)
const form = reactive({})
const selId = ref(null)
const kw = ref('')
const treeSel = ref('ROOT') // 'ROOT'=根分类（原版：选中根节点右侧列表为空）；null=未选
const catCollapsed = ref(false)
const whFilter = ref(null)
const page = ref(1)
const pageSize = computed(() => cfg.value.pageSize || 10)
const stockMap = ref({})

const treeNodes = computed(() => {
  // 层级化：按 parent_id 组树后深度优先展开（带缩进层级）；折叠的节点不显示下级
  const list = treeSrcList.value
  const byParent = {}
  for (const n of list) (byParent[n.parent_id || 0] = byParent[n.parent_id || 0] || []).push(n)
  // 同级按 sortval 排序（原版上移/下移持久化）
  for (const k in byParent) byParent[k].sort((a, b) => (a.sortval || 0) - (b.sortval || 0) || (a.id - b.id))
  const out = []
  const walk = (pid, depth) => {
    for (const n of (byParent[pid] || [])) {
      out.push({ id: n.id, name: n.name, depth, first: byParent[pid][0] === n, hasKids: !!byParent[n.id] })
      if (byParent[n.id] && !collapsedCats.has(n.id)) walk(n.id, depth + 1)
    }
  }
  walk(0, 0)
  const known = new Set(out.map(n => n.id))
  const allIds = new Set(list.map(n => n.id))
  // 只兜底"父节点不存在"的孤儿；折叠隐藏的不补（否则收起后下级跑到外层）
  for (const n of list) {
    if (!known.has(n.id) && !(n.parent_id && allIds.has(n.parent_id))) { out.push({ id: n.id, name: n.name, depth: 0, hasKids: false }); known.add(n.id) }
  }
  return out
})

/* 注册表式树：点名称/⊟⊞ 收起展开下级（默认全展开） */
const collapsedCats = reactive(new Set())
function toggleCat(id) { collapsedCats.has(id) ? collapsedCats.delete(id) : collapsedCats.add(id) }
function onCatClick(n) { treeSel.value = n.id; if (n.hasKids) toggleCat(n.id) }
const flatTree = treeNodes

// 选中分类后需过滤的分类集合（含其全部下级）；分类实体/期初以树源数据为准
const catFilterIds = computed(() => {
  if (treeSel.value == null || treeSel.value === 'ROOT') return null
  const list = treeSrcList.value
  const ids = new Set([treeSel.value])
  let grew = true
  while (grew) {
    grew = false
    for (const n of list) if (n.parent_id && ids.has(n.parent_id) && !ids.has(n.id)) { ids.add(n.id); grew = true }
  }
  return ids
})

function optsOf(fld) {
  const key = fld.ref === 'self' ? cfg.value.endpoint : fld.ref
  return options[key] || []
}

const filtered = computed(() => {
  // 选根分类（类别分类/货物分类等）= 显示全部记录
  let data = rows.value
  if (kw.value) {
    const k = kw.value.trim().toLowerCase()
    data = data.filter(r => [r.code, r.name].some(v => (v || '').toLowerCase().includes(k)))
  }
  if (whFilter.value && (cfg.value.isInitial || entity.value === 'locations')) {
    data = data.filter(r => r.warehouse_id === whFilter.value)
  }
  if (treeSel.value != null && treeSel.value !== 'ROOT' && (cfg.value.treeField || isCatEntity.value)) {
    const ids = catFilterIds.value
    data = data.filter(r => ids.has(cfg.value.treeField ? r[cfg.value.treeField] : r.id))
  } else if (treeSel.value != null && treeSel.value !== 'ROOT' && cfg.value.isInitial) {
    // 期初库存：按货物所属分类过滤
    const ids = catFilterIds.value
    data = data.filter(r => ids.has((options.goods || []).find(g => g.id === r.goods_id)?.goods_category_id))
  }
  return data
})
const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize.value)))
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

function disp(r, c) {
  if (c.key === 'cat') {
    if (entity.value === 'goods') return labelOf('goods-categories', r.goods_category_id)
    if (entity.value === 'locations') return labelOf('location-categories', r.location_category_id)
    return ''
  }
  if (c.key === 'parent') return labelOf('locations', r.parent_id)
  if (c.key === 'loc') {
    const n = labelOf('locations', r.default_location_id)
    return n ? n + '（默认）' : ''
  }
  if (c.key === 'wh') return labelOf('warehouses', r.warehouse_id)
  if (c.key === 'stock') return stockMap.value[r.code] ?? 0
  if (c.key === 'unit') {
    // 货物/期初：单位直接存为文本字段 unit；工作人员：单位=所属往来单位(unit_id)
    if (entity.value === 'personnel') return labelOf('units', r.unit_id)
    return r.unit ?? ''
  }
  if (c.key === 'dft') {
    if (entity.value === 'warehouses') return r.dft || ''
    if (entity.value === 'categories') return r.sel || ''
    if (entity.value === 'units' || entity.value === 'personnel') return r.dft || ''
    return ''
  }
  return r[c.key] ?? ''
}
function labelOf(refKey, id) {
  const o = (options[refKey] || []).find(x => x.id === id)
  return o ? o.name : ''
}

async function loadOptions() {
  const refs = new Set((cfg.value.fields || []).filter(f => f.ref && f.ref !== 'utypes').map(f => f.ref))
  if (cfg.value.treeSrc) refs.add(cfg.value.treeSrc)
  // 专属弹窗需要的下拉
  if (entity.value === 'goods') { refs.add('locations'); refs.add('warehouses') }
  if (cfg.value.isInitial) { refs.add('locations'); refs.add('warehouses'); refs.add('goods'); refs.add('goods-categories') }
  for (const rkey of refs) {
    const key = rkey === 'self' ? cfg.value.endpoint : rkey
    if (!options[key]) options[key] = await api.list(key)
  }
}
async function load() {
  if (cfg.value.isInitial) {
    rows.value = await api.list('initial-items')
    return
  }
  rows.value = await api.list(cfg.value.endpoint)
  if (entity.value === 'goods') {
    try {
      const inv = await api.list('inventory')
      const m = {}
      for (const r of inv) m[r.code] = (m[r.code] || 0) + (r.qty || 0)
      for (const k in m) m[k] = Math.round(m[k] * 100) / 100
      stockMap.value = m
    } catch (e) {}
  }
}

/* 分类实体（货物分类/单位分类/人员分类/进出类别）：树与表格同源，添加/编辑走原版"分类"小窗口 */
const isCatEntity = computed(() => ['goods-categories', 'unit-categories', 'personnel-categories'].includes(entity.value))

/* 左侧分类树的数据源 */
const treeSrcList = computed(() => {
  if (cfg.value.treeSrc) return options[cfg.value.treeSrc] || []
  if (isCatEntity.value) return rows.value
  if (cfg.value.isInitial) return options['goods-categories'] || []
  return []
})

/* 分类操作的存储源与上级拾取源（原版：工具条=分类操作，底部按钮=记录操作） */
const catSrc = computed(() => cfg.value.treeSrc
  || ((isCatEntity.value || entity.value === 'categories') ? cfg.value.endpoint : null)
  || (cfg.value.isInitial ? 'goods-categories' : null))
const catRef = computed(() => cfg.value.treeSrc
  || ((isCatEntity.value || entity.value === 'categories') ? 'self' : 'goods-categories'))

/* 底部"添加"按钮：针对表格记录（原版：货物资料→添加货物，期初→添加期初，进出类别→添加类别完整窗口） */
function openAddRecord() {
  if (cfg.value.isInitial) { openInitial(null); return }
  if (entity.value === 'goods') { openGoods(null); return }
  if (entity.value === 'categories') {
    // 原版：添加类别（完整窗口，各下拉初始为空；分类默认取左侧选中的树节点）
    editing.value = false
    for (const f of cfg.value.fields) form[f.key] = f.selOpts ? null : ''
    form.class_id = (treeSel.value && treeSel.value !== 'ROOT') ? treeSel.value : null
    visible.value = true
    return
  }
  if (isCatEntity.value) { openCatAdd(); return }
  editing.value = false
  for (const f of cfg.value.fields) form[f.key] = f.type === 'bool' ? 0 : (f.type === 'number' ? 0 : (f.selOpts ? null : ''))
  // 原版行为：左侧选了分类，新记录的分类默认挂到该分类
  if (cfg.value.treeField && treeSel.value && treeSel.value !== 'ROOT') form[cfg.value.treeField] = treeSel.value
  visible.value = true
}
function editSelected(row) {
  const r = row || rows.value.find(x => x.id === selId.value)
  if (!r) return ElMessage.info('请先选择一行')
  if (cfg.value.isInitial) { openInitial(r); return }
  if (entity.value === 'goods') { openGoods(r); return }
  if (entity.value === 'categories') {
    // 原版：编辑类别（完整窗口，带原数据）
    editing.value = true
    Object.keys(form).forEach(k => delete form[k])
    Object.assign(form, r)
    visible.value = true
    return
  }
  if (isCatEntity.value) {
    // 原版：编辑分类（弹出同一分类窗口，带原数据）
    Object.assign(catForm, { code: r.code || '', parent_id: r.parent_id || null, name: r.name || '', remark: r.remark || '', id: r.id })
    editing.value = true
    catVisible.value = true
    return
  }
  editing.value = true
  Object.keys(form).forEach(k => delete form[k])
  Object.assign(form, r)
  visible.value = true
}
async function removeSelected(row) {
  const r = row || rows.value.find(x => x.id === selId.value)
  if (!r) {
    // 未选中行但选中了左侧分类 → 删除该分类（原版行为）
    if (treeSel.value != null && treeSel.value !== 'ROOT') return removeCat()
    return ElMessage.info('请先选择一行')
  }
  const label = cfg.value.isInitial ? ('期初单 ' + r.doc_no) : (r.name || r.code)
  await ElMessageBox.confirm(`确认删除【${label}】？`, '删除', { type: 'warning' }).catch(() => Promise.reject())
  try {
    if (cfg.value.isInitial) await api.remove('initial', r.doc_id)
    else await api.remove(cfg.value.endpoint, r.id)
    ElMessage.success('已删除')
    load()
  } catch (e) { ElMessage.error(e.message) }
}

/* 工具条 ⬆⬇（原版）：左侧选中分类→移动分类；否则移动表格选中行 */
async function moveRow(dir) {
  try {
    if (treeSel.value != null && treeSel.value !== 'ROOT' && catSrc.value && !cfg.value.isInitial) {
      const src = catSrc.value
      const all = options[src] || []
      const node = all.find(n => n.id === treeSel.value)
      if (!node) return
      const sibs = all.filter(n => (n.parent_id || null) === (node.parent_id || null))
        .sort((a, b) => (a.sortval || 0) - (b.sortval || 0) || (a.id - b.id))
      const i = sibs.findIndex(n => n.id === treeSel.value)
      const j = i + dir
      if (j < 0 || j >= sibs.length) return
      const ids = sibs.map(n => n.id)
      ;[ids[i], ids[j]] = [ids[j], ids[i]]
      await api.raw.post('/' + src + '/reorder', { ids })
      options[src] = await api.list(src)
      if (isCatEntity.value) load()
      return
    }
    const vis = filtered.value
    const fi = vis.findIndex(x => x.id === selId.value)
    if (fi < 0) return ElMessage.info('请先选择一行')
    const fj = fi + dir
    if (fj < 0 || fj >= vis.length) return
    const idA = vis[fi].id, idB = vis[fj].id
    if (cfg.value.isInitial) {  // 期初明细无独立排序字段，仅本地调整显示顺序
      const gi = rows.value.findIndex(x => x.id === idA)
      const gj = rows.value.findIndex(x => x.id === idB)
      ;[rows.value[gi], rows.value[gj]] = [rows.value[gj], rows.value[gi]]
      return
    }
    const ids = rows.value.map(r => r.id)
    const gi = ids.indexOf(idA), gj = ids.indexOf(idB)
    ;[ids[gi], ids[gj]] = [ids[gj], ids[gi]]
    await api.raw.post('/' + cfg.value.endpoint + '/reorder', { ids })
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function save() {
  /* 通用必填校验（红*字段） */
  for (const f of cfg.value.fields) {
    if (f.required && (form[f.key] === '' || form[f.key] == null))
      return ElMessage.warning(`「${f.label}」为必选项，请填写或选择后再保存`)
  }
  /* 原版校验（VBA eMsgZjlr/eMsgDbpd） */
  if (entity.value === 'categories') {
    if (form.zjlr === '是' && !['出货正数', '出货负数'].includes(form.jxtj))
      return ElMessage.warning('当“增减利润”选择的数值为“是”时，“进销统计”必须选择“出货正数”或“出货负数”')
    if (form.jxtj === '调拨盘点' && (form.xygh === '是' || form.kjdh === '是'))
      return ElMessage.warning('当“进销统计”选择数值为“调拨盘点”时，“需要归还”与“扣减待还”必须选择“否”')
  }
  try {
    if (editing.value) await api.update(cfg.value.endpoint, form.id, { ...form })
    else await api.create(cfg.value.endpoint, { ...form })
    ElMessage.success('已保存')
    visible.value = false
    load()
  } catch (e) { ElMessage.error(e.message) }
}

/* ---------- 分类管理（树面板） ---------- */
const catVisible = ref(false)
const catForm = reactive({ code: '', parent_id: null, name: '', remark: '' })

function openCatAdd() {
  Object.assign(catForm, { code: '', parent_id: treeSel.value === 'ROOT' ? null : treeSel.value, name: '', remark: '', id: null })
  editing.value = false
  catVisible.value = true
}
/* 工具条 🗑 / ✏：针对左侧选中的分类（原版行为） */
function removeCatBtn() {
  if (treeSel.value == null || treeSel.value === 'ROOT') return ElMessage.info('请先在左侧选择分类')
  removeCat()
}
function editCatBtn() {
  if (treeSel.value == null || treeSel.value === 'ROOT') return ElMessage.info('请先在左侧选择分类')
  const n = treeSrcList.value.find(x => x.id === treeSel.value)
  if (!n) return ElMessage.info('请先在左侧选择分类')
  Object.assign(catForm, { code: n.code || '', parent_id: n.parent_id || null, name: n.name || '', remark: n.remark || '', id: n.id })
  editing.value = true
  catVisible.value = true
}
async function saveCat() {
  if (!catForm.name || !catForm.name.trim()) return ElMessage.warning('请填写分类名称')
  const src = catSrc.value
  if (!src) return
  try {
    if (editing.value && catForm.id) {
      await api.update(src, catForm.id, { ...catForm })
    } else {
      await api.create(src, { ...catForm })
    }
    ElMessage.success('已保存')
    catVisible.value = false
    // 分类实体窗口：树与表格同源，两处都刷新
    options[src] = await api.list(src)
    load()
  } catch (e) { ElMessage.error(e.message) }
}
async function removeCat() {
  if (treeSel.value == null || treeSel.value === 'ROOT') return
  const src = catSrc.value
  if (!src) return
  const n = treeSrcList.value.find(x => x.id === treeSel.value)
  const hasChildren = (options[src] || []).some(x => x.parent_id === treeSel.value)
  if (hasChildren) return ElMessage.warning('该分类存在下级分类，请先删除下级')
  await ElMessageBox.confirm(`确认删除分类【${n ? n.name : ''}】？`, '提示', { type: 'warning' }).catch(() => Promise.reject())
  try {
    await api.remove(src, treeSel.value)
    ElMessage.success('分类已删除')
    treeSel.value = 'ROOT'
    if (cfg.value.treeSrc) options[src] = await api.list(src)
    if (isCatEntity.value) load()
  } catch (e) { ElMessage.error(e.message) }
}

/* ---------- 通用拾取窗口（原版：人员→所属单位弹往来单位；货物→默认库位弹库区库位；期初→货物/仓库/库位弹对应资料窗口） ---------- */
const PICK_TITLES = { units: '往来单位', locations: '库区库位', goods: '货物资料', warehouses: '仓库信息' }
const winPickOn = ref(false)
const winPickEntity = ref('units')
let winPickField = null
function openWinPick(fld) {
  winPickField = fld
  winPickEntity.value = typeof fld.pickWin === 'string' ? fld.pickWin : 'units'
  winPickOn.value = true
}
async function onUnitPicked(id) {
  if (winPickField) {
    if (winPickField.key === '__whfilter') whFilter.value = id // 库区库位「所有仓库」筛选
    else {
      form[winPickField.key] = id
      // 原版逻辑：换了仓库，之前选的库位不再有效
      if (winPickField.key === 'warehouse_id') form.location_id = null
    }
  }
  winPickOn.value = false
  // 刷新外层下拉数据，确保新添加的记录能立即显示名称
  try { options[winPickEntity.value] = await api.list(winPickEntity.value) } catch (e) {}
}
/* 原版：库区库位窗口点「所有仓库」弹出仓库信息选取窗 */
function openWhPick() {
  openWinPick({ key: '__whfilter', pickWin: 'warehouses' })
}
function goodsLabel(id) {
  const g = (options.goods || []).find(x => x.id === id)
  return g ? (g.code ? g.code + ' ' : '') + g.name : ''
}
/* ---------- 职务"选择数据"小窗（原版：确定/清空/添加/删除/编辑） ---------- */
const dpk = reactive({ on: false, key: '', rows: [], sel: null, static: null })
const dpkFormOn = ref(false)
const dpkEditing = ref(false)
const dpkForm = reactive({ code: '', name: '', remark: '', id: null })

async function openDataPick(fld) {
  dpk.key = fld.key
  dpk.sel = null
  if (fld.pickOpts) {
    // 静态选项模式（原版库位"默认"：无/全部/新货物/智能库位），无增删改
    dpk.static = fld.pickOpts
    dpk.rows = fld.pickOpts.map((n, i) => ({ id: -(i + 1), name: n }))
  } else {
    dpk.static = null
    try { dpk.rows = await api.list('personnel-titles') } catch (e) { dpk.rows = [] }
  }
  dpk.on = true
}
function dpkOk() {
  const r = dpk.rows.find(x => x.id === dpk.sel)
  if (!r) return ElMessage.info('请先在列表中选择一条职务')
  form[dpk.key] = r.name
  dpk.on = false
}
function dpkClear() {
  form[dpk.key] = ''
  dpk.on = false
}
function dpkAdd() {
  if (dpk.static) return
  Object.assign(dpkForm, { code: '', name: '', remark: '', id: null })
  dpkEditing.value = false
  dpkFormOn.value = true
}
function dpkEdit() {
  if (dpk.static) return
  const r = dpk.rows.find(x => x.id === dpk.sel)
  if (!r) return ElMessage.info('请先在列表中选择一条职务')
  Object.assign(dpkForm, { code: r.code || '', name: r.name || '', remark: r.remark || '', id: r.id })
  dpkEditing.value = true
  dpkFormOn.value = true
}
async function dpkSave() {
  if (!dpkForm.name || !dpkForm.name.trim()) return ElMessage.warning('请填写名称')
  try {
    if (dpkEditing.value && dpkForm.id) await api.update('personnel-titles', dpkForm.id, { ...dpkForm })
    else await api.create('personnel-titles', { ...dpkForm })
    dpkFormOn.value = false
    dpk.rows = await api.list('personnel-titles')
  } catch (e) { ElMessage.error(e.message) }
}
async function dpkDel() {
  if (dpk.static) return
  const r = dpk.rows.find(x => x.id === dpk.sel)
  if (!r) return ElMessage.info('请先在列表中选择一条职务')
  await ElMessageBox.confirm(`确认删除职务【${r.name}】？`, '提示', { type: 'warning' }).catch(() => Promise.reject())
  try {
    await api.remove('personnel-titles', r.id)
    dpk.rows = await api.list('personnel-titles')
  } catch (e) { ElMessage.error(e.message) }
}

/* ---------- 批量导入（原版：点导入弹表格，从 Excel 复制后 Ctrl+V 粘贴 → 检查 → 导入） ---------- */
const IMPORT_COLS = {
  goods: {
    basic: [
      { key: 'code', label: '编码', w: '70px' }, { key: 'name', label: '名称', req: true },
      { key: 'spec', label: '规格' }, { key: 'model', label: '型号' },
      { key: 'unit', label: '单位', w: '50px' },
      { key: 'catName', label: '分类', w: '90px', catRef: 'goods-categories', catKey: 'goods_category_id' },
      { key: 'min_stock', label: '最低库存', w: '60px', num: true }, { key: 'max_stock', label: '最高库存', w: '60px', num: true },
      { key: 'in_price', label: '入库单价', w: '62px', num: true }, { key: 'out_price', label: '出库单价', w: '62px', num: true },
      { key: 'transfer_price', label: '调拨单价', w: '62px', num: true }, { key: 'chk_price', label: '盘点单价', w: '62px', num: true },
      { key: 'enabled', label: '启用', w: '44px' }, { key: 'remark', label: '备注' },
    ],
    groups: ['期初仓库1', '期初仓库2', '期初仓库3'],
    qcSub: [
      { key: 'wh', label: '仓库', w: '70px', ref: 'warehouses' },
      { key: 'loc', label: '库位', w: '70px', ref: 'locations' },
      { key: 'qty', label: '数量', w: '56px', num: true },
      { key: 'price', label: '单价', w: '56px', num: true },
      { key: 'amount', label: '金额', w: '56px', num: true },
    ],
  },
  units: {
    basic: [
      { key: 'code', label: '编码', w: '90px' }, { key: 'name', label: '名称', req: true },
      { key: 'catName', label: '分类', w: '110px', catRef: 'unit-categories', catKey: 'unit_category_id' },
      { key: 'contact', label: '联系人', w: '90px' }, { key: 'phone', label: '电话', w: '110px' },
      { key: 'address', label: '地址' }, { key: 'remark', label: '备注' },
    ],
    groups: [], qcSub: [],
  },
}
const impBasic = computed(() => (IMPORT_COLS[entity.value] || {}).basic || [])
const impGroups = computed(() => (IMPORT_COLS[entity.value] || {}).groups || [])
const impQcSub = computed(() => (IMPORT_COLS[entity.value] || {}).qcSub || [])
const impCols = computed(() => {
  const flat = [...impBasic.value]
  impGroups.value.forEach((_, gi) => impQcSub.value.forEach(s => flat.push({ ...s, key: 'qc' + (gi + 1) + '_' + s.key })))
  return flat
})
const impRows = ref([])
const impSel = ref(null)
const impMsg = ref('')
const impBad = ref(false)

function impAddRows(n) { for (let i = 0; i < n; i++) impRows.value.push({ tip: '' }) }
function impClear() { impRows.value = []; impSel.value = null; impMsg.value = ''; impBad.value = false }

function impPaste(e) {
  const text = (e.clipboardData || window.clipboardData)?.getData('text/plain')
  // 单元格里的普通文本粘贴走浏览器默认行为；带制表符/换行的整块数据按表格解析
  if (!text || (text.indexOf('\t') < 0 && text.indexOf('\n') < 0)) return
  e.preventDefault()
  const lines = text.replace(/\r/g, '').split('\n').filter(l => l.trim() !== '')
  const cols = impCols.value
  for (const ln of lines) {
    const cells = ln.split('\t')
    const rec = { tip: '' }
    cols.forEach((c, i) => { rec[c.key] = (cells[i] ?? '').trim() })
    impRows.value.push(rec)
  }
  impSel.value = impRows.value.length - 1
  impMsg.value = `已粘贴 ${lines.length} 行，请先「检查」再「导入」`
  impBad.value = false
}

function impCheck(silent) {
  const cols = impCols.value
  let ok = 0, bad = 0
  const names = new Set()
  for (const r of impRows.value) {
    r.tip = ''
    r._catId = null
    if (!r.name) { r.tip = '✗ 名称必填'; bad++; continue }
    if (names.has(r.name)) { r.tip = '✗ 表内名称重复'; bad++; continue }
    names.add(r.name)
    const cat = cols.find(c => c.catKey)
    if (cat && r.catName) {
      const o = (options[cat.catRef] || []).find(x => (x.name || '').trim() === r.catName.trim())
      if (!o) { r.tip = '✗ 分类「' + r.catName + '」不存在'; bad++; continue }
      r._catId = o.id
    }
    // 期初仓库组校验：填了数量必须给仓库；仓库/库位按名称匹配
    let qcErr = ''
    impGroups.value.forEach((_, gi) => {
      const p = 'qc' + (gi + 1) + '_'
      const whN = (r[p + 'wh'] || '').trim(), locN = (r[p + 'loc'] || '').trim()
      const qty = Number(r[p + 'qty']) || 0
      r['_qc' + (gi + 1)] = null
      if (!whN && !qty && !locN) return
      if (qty > 0 && !whN) { qcErr = '期初仓库' + (gi + 1) + '缺仓库名'; return }
      const wh = (options.warehouses || []).find(x => (x.name || '').trim() === whN)
      if (whN && !wh) { qcErr = '仓库「' + whN + '」不存在'; return }
      let loc = null
      if (locN) {
        loc = (options.locations || []).find(x => (x.name || '').trim() === locN && (!wh || x.warehouse_id === wh.id))
          || (options.locations || []).find(x => (x.name || '').trim() === locN)
        if (!loc) { qcErr = '库位「' + locN + '」不存在'; return }
      }
      r['_qc' + (gi + 1)] = { warehouse_id: wh ? wh.id : null, location_id: loc ? loc.id : null, qty, price: Number(r[p + 'price']) || 0 }
    })
    if (qcErr) { r.tip = '✗ ' + qcErr; bad++; continue }
    r.tip = '✓ 可导入'; ok++
  }
  if (!silent) {
    impMsg.value = `检查完成：可导入 ${ok} 条` + (bad ? `，${bad} 条有误（见提示列）` : '')
    impBad.value = bad > 0
  }
  return { ok, bad }
}

async function impImport() {
  if (!impRows.value.length) return ElMessage.info('请先粘贴或输入数据')
  const { ok, bad } = impCheck(true)
  if (!ok) { impMsg.value = `没有可导入的数据（${bad} 条有误，见提示列）`; impBad.value = true; return }
  if (bad && !window.confirm(`有 ${bad} 条有误将被跳过，只导入 ${ok} 条，继续吗？`)) return
  let done = 0, fail = 0
  const cols = impCols.value
  for (const r of impRows.value) {
    if (r.tip !== '✓ 可导入') continue
    const payload = {}
    for (const c of cols) {
      if (c.catKey) { if (r._catId) payload[c.catKey] = r._catId; continue }
      if (c.key === 'enabled') { payload.enabled = ['否', '0', '禁用'].includes((r.enabled || '').trim()) ? 0 : 1; continue }
      payload[c.key] = c.num ? (Number(r[c.key]) || 0) : (r[c.key] || '')
    }
    payload.code = (r.code || '').trim() // 留空则后端自动编码
    try {
      const created = await api.create(cfg.value.endpoint, payload)
      done++
      // 期初库存：每组"期初仓库N"按其仓库分别建期初单（原版导入表逻辑）
      for (let gi = 1; gi <= impGroups.value.length; gi++) {
        const qc = r['_qc' + gi]
        if (!qc || !qc.warehouse_id || !(qc.qty > 0)) continue
        await api.post('initial', {
          date: todayStr(), warehouse_id: qc.warehouse_id, operator: '', remark: '批量导入',
          items: [{ goods_id: created.id, location_id: qc.location_id, qty: qc.qty, price: qc.price, amount: Math.round(qc.qty * qc.price * 100) / 100, remark: '' }],
        })
      }
    }
    catch (e) { fail++; r.tip = '✗ ' + (e.message || '导入失败') }
  }
  impMsg.value = `导入完成：成功 ${done} 条` + (fail ? `，失败 ${fail} 条` : '')
  impBad.value = fail > 0
  if (done) {
    impRows.value = impRows.value.filter(r => r.tip !== '✓ 可导入')
    impSel.value = null
    load(); loadOptions()
  }
}

/* 拾取模式：把当前选中行回传给父窗口（按钮或双击行） */
function doPick(row) {
  const r = row || rows.value.find(x => x.id === selId.value)
  if (!r) return ElMessage.info('请先在列表中选择一条记录')
  emit('pick', r.id, r.name)
}

/* ---------- 选择分类拾取器（虚线树+展开框，右侧七按钮：确定/清空/添加/删除/编辑/上移/下移） ---------- */
const picker = reactive({ on: false, form: null, key: '', src: '', list: [] })
const cat2On = ref(false)
const cat2Editing = ref(false)
const catForm2 = reactive({ code: '', parent_id: null, name: '', remark: '', id: null })
const selPid = ref(null)
const pickExpanded = reactive(new Set())

/* 可折叠树：仅展开已点开的节点（原版行为） */
const pickNodes = computed(() => {
  const all = options[picker.src] || []
  const byParent = {}
  for (const n of all) (byParent[n.parent_id || 0] = byParent[n.parent_id || 0] || []).push(n)
  for (const k in byParent) byParent[k].sort((a, b) => (a.sortval || 0) - (b.sortval || 0) || (a.id - b.id))
  const out = []
  const walk = (pid, depth) => {
    for (const n of (byParent[pid] || [])) {
      const hasKids = (byParent[n.id] || []).length > 0
      out.push({ id: n.id, name: n.name, depth, hasKids })
      if (hasKids && pickExpanded.has(n.id)) walk(n.id, depth + 1)
    }
  }
  walk(0, 0)
  // 兜底：父级缺失的脏数据也显示出来
  const known = new Set(out.map(n => n.id))
  for (const n of all) if (!known.has(n.id) && n.parent_id && !all.find(x => x.id === n.parent_id)) out.push({ id: n.id, name: n.name, depth: 0, hasKids: false })
  return out
})
function togglePick(id) { pickExpanded.has(id) ? pickExpanded.delete(id) : pickExpanded.add(id) }

function isCatRef(fld) { return fld.ref === 'self' || /categor/.test(fld.ref) }

function hierList(list) {
  const byParent = {}
  for (const n of list) (byParent[n.parent_id || 0] = byParent[n.parent_id || 0] || []).push(n)
  for (const k in byParent) byParent[k].sort((a, b) => (a.sortval || 0) - (b.sortval || 0) || (a.id - b.id))
  const out = []
  const walk = (pid, depth) => {
    for (const n of (byParent[pid] || [])) { out.push({ id: n.id, name: n.name, depth }); walk(n.id, depth + 1) }
  }
  walk(0, 0)
  const known = new Set(out.map(n => n.id))
  for (const n of list) if (!known.has(n.id)) { out.push({ id: n.id, name: n.name, depth: 0 }); known.add(n.id) }
  return out
}

function openPicker(fld) {
  const src = fld.ref === 'self' ? cfg.value.endpoint : fld.ref
  picker.src = src
  picker.form = fld.form || form
  picker.key = fld.key
  picker.list = hierList(options[src] || [])
  selPid.value = (fld.form || form)[fld.key] ?? null
  // 展开当前选中节点的全部祖先，保证选中项可见
  pickExpanded.clear()
  if (selPid.value) {
    const all = options[src] || []
    const byId = new Map(all.map(n => [n.id, n]))
    let cur = byId.get(selPid.value)
    while (cur && cur.parent_id) { pickExpanded.add(cur.parent_id); cur = byId.get(cur.parent_id) }
  }
  picker.on = true
}
function refName(fld) {
  const v = form[fld.key]
  if (!v) return ''
  const o = optsOf(fld).find(x => x.id === v)
  return o ? o.name : ''
}
function parentName(id) {
  if (!id) return ''
  const o = (options[catSrc.value] || []).find(x => x.id === id)
  return o ? o.name : ''
}
function pickOk() { picker.form[picker.key] = selPid.value; picker.on = false }
function pickClear() { picker.form[picker.key] = null; picker.on = false }
function openCat2() {
  Object.assign(catForm2, { code: '', parent_id: selPid.value, name: '', remark: '', id: null })
  cat2Editing.value = false
  cat2On.value = true
}
/* 编辑选中的分类（复用添加弹窗） */
function pickEdit() {
  if (!selPid.value) return ElMessage.info('请先选择分类')
  const n = (options[picker.src] || []).find(x => x.id === selPid.value)
  if (!n) return ElMessage.info('请先选择分类')
  Object.assign(catForm2, { code: n.code || '', parent_id: n.parent_id || null, name: n.name || '', remark: n.remark || '', id: n.id })
  cat2Editing.value = true
  cat2On.value = true
}
/* 编辑时上级下拉排除自己与自己的下级（防环） */
const pickParentOpts = computed(() => {
  let list = options[picker.src] || []
  if (cat2Editing.value && catForm2.id) {
    const bad = new Set([catForm2.id])
    let grew = true
    while (grew) { grew = false; for (const n of list) if (n.parent_id && bad.has(n.parent_id) && !bad.has(n.id)) { bad.add(n.id); grew = true } }
    list = list.filter(n => !bad.has(n.id))
  }
  return list
})
/* 删除选中的分类（存在下级先提示；被记录引用时后端返回中文错误） */
async function pickDel() {
  if (!selPid.value) return ElMessage.info('请先选择分类')
  const src = picker.src
  const n = (options[src] || []).find(x => x.id === selPid.value)
  const hasKids = (options[src] || []).some(x => x.parent_id === selPid.value)
  if (hasKids) return ElMessage.warning('该分类存在下级分类，请先删除下级')
  await ElMessageBox.confirm(`确认删除分类【${n ? n.name : ''}】？`, '提示', { type: 'warning' }).catch(() => Promise.reject())
  try {
    await api.remove(src, selPid.value)
    ElMessage.success('分类已删除')
    selPid.value = null
    options[src] = await api.list(src)
    picker.list = hierList(options[src] || [])
    if (cfg.value.treeSrc === src || catSrc.value === src) load()
  } catch (e) { ElMessage.error(e.message) }
}
/* 上移/下移选中分类（持久化 sortval） */
async function pickMove(dir) {
  if (!selPid.value) return ElMessage.info('请先选择分类')
  const src = picker.src
  const all = options[src] || []
  const node = all.find(n => n.id === selPid.value)
  if (!node) return
  const sibs = all.filter(n => (n.parent_id || null) === (node.parent_id || null))
    .sort((a, b) => (a.sortval || 0) - (b.sortval || 0) || (a.id - b.id))
  const i = sibs.findIndex(n => n.id === selPid.value)
  const j = i + dir
  if (j < 0 || j >= sibs.length) return
  const ids = sibs.map(n => n.id)
  ;[ids[i], ids[j]] = [ids[j], ids[i]]
  try {
    await api.raw.post('/' + src + '/reorder', { ids })
    options[src] = await api.list(src)
    picker.list = hierList(options[src] || [])
    if (cfg.value.treeSrc === src || catSrc.value === src) load()
  } catch (e) { ElMessage.error(e.message) }
}
async function saveCat2() {
  if (!catForm2.name.trim()) return ElMessage.warning('请填写分类名称')
  try {
    if (cat2Editing.value && catForm2.id) await api.update(picker.src, catForm2.id, { ...catForm2 })
    else await api.create(picker.src, { ...catForm2 })
    ElMessage.success('分类已保存')
    cat2On.value = false
    options[picker.src] = await api.list(picker.src)
    picker.list = hierList(options[picker.src] || [])
    if (cfg.value.treeSrc === picker.src || catSrc.value === picker.src) load()
  } catch (e) { ElMessage.error(e.message) }
}

/* ---------- 添加/编辑货物（原版窗口，含期初库存子表） ---------- */
const goodsVisible = ref(false)
const UNIT_OPTS = ['个', '件', '箱', '套', '台', '只', '张', '公斤', '克', '升', '米', '卷', '包', '桶']
const qcRows = ref([])
const qcSel = ref(null)

function openGoods(r) {
  editing.value = !!r
  Object.keys(form).forEach(k => delete form[k])
  Object.assign(form, r ? { ...r } : {
    code: '', name: '', spec: '', model: '', unit: '', goods_category_id: null,
    min_stock: 0, max_stock: 0, purchase_price: 0, sale_price: 0,
    in_price: 0, out_price: 0, transfer_price: 0, chk_price: 0,
    default_location_id: null, remark: '', enabled: 1,
  })
  // 原版行为：左侧选了分类，新货物的分类默认挂到该分类（否则会被分类过滤隐藏）
  if (!r && treeSel.value && treeSel.value !== 'ROOT') form.goods_category_id = treeSel.value
  qcRows.value = []
  qcSel.value = null
  goodsVisible.value = true
}
function locsOfWh(whId) {
  const list = options.locations || []
  return whId ? list.filter(l => l.warehouse_id === whId) : list
}
function qcAdd() { qcRows.value.push({ warehouse_id: null, location_id: null, qty: 0, price: 0, amount: 0, remark: '' }); qcSel.value = qcRows.value.length - 1 }
function qcDel() {
  if (qcSel.value == null) return
  qcRows.value.splice(qcSel.value, 1)
  qcSel.value = null
}
function qcCalc(q) { q.amount = Math.round((q.qty || 0) * (q.price || 0) * 100) / 100 }
function fmtAmt(v) { return (v == null || isNaN(v)) ? '' : String(Math.round(v * 100) / 100) }
function qcEdit() {
  if (qcSel.value == null) return ElMessage.info('请先选择一行期初库存')
  nextTick(() => {
    const el = document.querySelector('.qc-grid tr.sel td .qc-input')
    if (el) el.focus()
  })
}
async function saveGoods() {
  if (!form.name || !form.name.trim()) return ElMessage.warning('请填写名称')
  try {
    if (editing.value) {
      await api.update('goods', form.id, { ...form })
    } else {
      const d = await api.create('goods', { ...form })
      const gid = d.id
      for (const q of qcRows.value) {
        if (!q.warehouse_id || !(q.qty > 0)) continue
        await api.post('initial', {
          date: todayStr(), warehouse_id: q.warehouse_id, operator: '', remark: q.remark || '',
          items: [{ goods_id: gid, warehouse_id: q.warehouse_id, location_id: q.location_id, qty: q.qty || 0, price: q.price || 0, remark: q.remark || '' }],
        })
      }
    }
    ElMessage.success('已保存')
    goodsVisible.value = false
    load()
  } catch (e) { ElMessage.error(e.message) }
}
function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/* ---------- 添加/编辑期初（原版窗口） ---------- */
const initialVisible = ref(false)

function openInitial(r) {
  editing.value = !!r
  Object.keys(form).forEach(k => delete form[k])
  if (r) {
    Object.assign(form, { doc_id: r.doc_id, goods_id: r.goods_id, warehouse_id: r.warehouse_id, location_id: r.location_id, qty: r.qty, price: r.price, amount: r.amount, remark: r.remark || '' })
  } else {
    Object.assign(form, { goods_id: null, warehouse_id: null, location_id: null, qty: 0, price: 0, amount: 0, remark: '' })
  }
  initialVisible.value = true
}
function calcAmount() { form.amount = Math.round((form.qty || 0) * (form.price || 0) * 100) / 100 }
async function saveInitial() {
  if (!form.goods_id) return ElMessage.warning('请选择货物')
  if (!form.warehouse_id) return ElMessage.warning('请选择仓库')
  const item = { goods_id: form.goods_id, warehouse_id: form.warehouse_id, location_id: form.location_id, qty: form.qty || 0, price: form.price || 0, amount: form.amount || 0, remark: form.remark || '' }
  try {
    if (editing.value) {
      const head = await api.get(`initial/${form.doc_id}`)
      await api.update('initial', form.doc_id, {
        date: head.header.date, operator: head.header.operator, remark: form.remark || head.header.remark || '',
        items: [item],
      })
    } else {
      await api.post('initial', { date: todayStr(), warehouse_id: form.warehouse_id, operator: '', remark: form.remark || '', items: [item] })
    }
    ElMessage.success('已保存')
    initialVisible.value = false
    load()
  } catch (e) { ElMessage.error(e.message) }
}

watch(() => props.entity || route.params.entity, async (e) => {
  entity.value = e
  page.value = 1; selId.value = null; treeSel.value = 'ROOT'; kw.value = ''; whFilter.value = null
  await loadOptions(); load()
})
onMounted(async () => { await loadOptions(); if (props.pickMode) treeSel.value = null; load() })
</script>

<style scoped>
tr.sel td { background: #ffe9a8 !important; }
.tree-head { display: flex; align-items: center; padding: 2px 6px 6px; }
.tree-head b { font-size: 13px; color: var(--ku-text); }
.tree-btn { cursor: pointer; font-size: 14px; padding: 1px 3px; }
.tree-btn:hover { background: var(--ku-hover); }
.pick-field { display: flex; align-items: center; width: 100%; border: 1px solid #dcdfe6; border-radius: 4px; background: #fff; cursor: pointer; }
.pick-field:hover { border-color: var(--ku-accent); }
.pick-val { flex: 1; padding: 5px 10px; font-size: 14px; color: var(--ku-text); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.pick-val.ph { color: #a8abb2; }
.pick-ico { padding: 0 8px; color: var(--ku-accent); }
.pick-wrap { display: flex; gap: 6px; }
/* 库区库位底部「所有仓库」选取框（原版：只读框+下拉箭头，点击弹仓库信息窗） */
.wh-pick { display: inline-flex; align-items: center; width: 150px; height: 28px; border: 1px solid var(--ku-border, #c8d4e0); border-radius: 4px; background: #fff; cursor: pointer; }
.wh-pick:hover { border-color: var(--ku-accent); }
.wh-pick-val { flex: 1; padding: 0 8px; font-size: 12px; color: var(--ku-text); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.wh-pick-val.ph { color: #a8abb2; }
.wh-pick-ico { padding: 0 6px; font-size: 10px; color: var(--ku-accent); }
.dpk-list { flex: 1; height: 260px; overflow: auto; border: 1px solid var(--ku-border); background: #fff; }
.dpk-row { padding: 7px 12px; cursor: pointer; }
.dpk-row:hover { background: #f5f7fa; }
.dpk-row.sel { background: var(--ku-accent); color: #fff; }
.dpk-empty { padding: 16px 12px; color: #999; font-size: 12px; }
.pick-tree { flex: 1; height: 260px; overflow: auto; border: 1px solid var(--ku-border); background: #fff; padding: 4px; }
.pick-node { padding: 4px 8px; cursor: pointer; font-size: 13px; color: var(--ku-text); display: flex; align-items: center; }
.pick-node:hover { background: var(--ku-hover); }
.pick-node.sel { background: var(--ku-sel); }
.pick-node.sel .pick-name { color: #fff; }
.pick-name { flex: 1; }
.pick-tree-dotted .pick-node .tv-box { margin-right: 4px; flex: 0 0 auto; }
.pick-btns { display: flex; flex-direction: column; gap: 6px; }
.pick-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--ku-border); background: var(--ku-head); cursor: pointer; font-size: 15px; }
.pick-btn:hover { background: var(--ku-hover); }
.fg2 { display: grid; grid-template-columns: 1fr 1fr; column-gap: 20px; }
.fg2 .full { grid-column: 1 / -1; }
/* 嵌套"往来单位"选取窗口 */
.unit-pick-body { height: 62vh; display: flex; }
.unit-pick-body .ku-win { flex: 1; min-width: 0; }
.unit-pick-dlg .ku-win-main { max-height: none; height: calc(100% - 54px); }
.qc-box { border: 1px solid var(--ku-border); background: var(--ku-panel-soft); padding: 8px; margin-top: 4px; }
.qc-head { display: flex; align-items: center; gap: 6px; padding-bottom: 6px; }
.qc-head b { font-size: 13px; color: var(--ku-text); }
/* 原版风格：期初库存工具条三个方形大图标（添加/删除/编辑） */
.qc-tools { display: flex; gap: 4px; }
.qc-ico-btn {
  width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--ku-border); border-radius: 3px; background: #fff;
  color: var(--ku-text); cursor: pointer; flex: none;
}
.qc-ico-btn svg { width: 19px; height: 19px; }
.qc-ico-btn:hover { border-color: var(--ku-accent); color: var(--ku-accent); background: #eaf3fb; }
.qc-ico-btn:active { background: #d8e9f8; }
/* 批量导入表格（原版"导入"表：从 Excel 粘贴） */
.imp-wrap { outline: none; }
.imp-tip { font-size: 12px; color: var(--ku-text-soft, #667); background: var(--ku-panel-soft, #f4f8fb); border: 1px solid var(--ku-border); padding: 6px 10px; margin-bottom: 8px; border-radius: 4px; }
.imp-scroll { max-height: 52vh; overflow: auto; border: 1px solid var(--ku-border); }
.imp-grid { width: 100%; background: #fff; border-collapse: collapse; }
.imp-grid th { position: sticky; top: 0; background: var(--ku-panel-soft, #eef4f9); font-size: 12px; padding: 5px 6px; z-index: 1; }
.imp-grid th.grp { background: #d8e9f8; border-left: 1px solid var(--ku-border); }
.imp-grid td { padding: 1px 2px; border-bottom: 1px solid #f0f0f0; }
.imp-grid td.tip { font-size: 12px; padding: 2px 6px; color: #2a8a3e; white-space: nowrap; }
.imp-grid tr.bad td.tip { color: #d33; }
.imp-grid tr.sel td { background: #f2f8ff; }
.imp-grid tr.sel td.tip, .imp-grid tr.bad td { background: #fff4f2; }
.imp-input { width: 100%; box-sizing: border-box; border: 1px solid transparent; background: transparent; font: inherit; font-size: 12px; padding: 3px 4px; color: var(--ku-text); }
.imp-input:focus { outline: none; border-color: var(--ku-accent); background: #fff; }
.imp-bar { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.imp-msg { font-size: 12px; color: #2a8a3e; }
.imp-msg.bad { color: #d33; }
.imp-go { background: var(--ku-accent); color: #fff; border-color: var(--ku-accent); }
.qc-grid { width: 100%; background: #fff; }
.qc-grid th { font-size: 12px; padding: 4px 6px; }
.qc-grid td { padding: 2px 3px; }
.qc-input { width: 100%; box-sizing: border-box; border: 1px solid transparent; background: transparent; font: inherit; font-size: 13px; padding: 2px 3px; color: var(--ku-text); }
.qc-amt { text-align: right; padding: 2px 6px; font-size: 13px; color: var(--ku-text); }
.qc-input:focus { outline: none; border-color: var(--ku-accent); background: #fff; }
.qc-grid tr.sel td { background: #ffe9a8 !important; }
</style>
