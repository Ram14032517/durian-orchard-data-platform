"""Phase 10G: sealed-data display only; no overlay, repair, ML or network."""
from collections import defaultdict
from html import escape
from pathlib import Path
import math
import shapefile
import shapely
from shapely.geometry import shape
from tools import build_tha_mai_spatial_pilot as p
from tools import run_tha_mai_acceptance_policy as f

OUT=f.d.BASE/"phase10g_20261012_advisor_preview_v2"
SPECIAL={"SC","W","UNCOVERED"}


def display_groups(rows):
    ordinary=sorted((r for r in rows if r["soil_unit"] not in SPECIAL),key=lambda r:-r["area_rai"])
    top={r["soil_unit"] for r in ordinary[:6]}
    groups=defaultdict(float)
    for row in rows:
        key=row["soil_unit"] if row["soil_unit"] in top|SPECIAL else "OTHER"
        groups[key]+=row["area_rai"]
    assert math.isclose(sum(groups.values()),sum(r["area_rai"] for r in rows),abs_tol=1e-8)
    return top,dict(groups)


def main():
    root=p.ROOT; out=root/OUT; release=root/f.RELEASE
    assert out.exists() and not (out/"map_preview.png").exists(),"Refuse overwrite"
    before=p.read_json(out/"preflight_protected_hashes.json")
    p.previous.verify_seal(root,f.OUT); p.previous.verify_seal(root,f.RELEASE)
    meta=p.read_json(release/"release_metadata.json"); summary=p.read_json(root/f.OUT/"summary.json")
    assert meta["public_release"]=="HOLD" and summary["status"]=="pass"
    assert p.sha(release/"dataset.json")==meta["dataset_sha256"]
    sources=p.read_json(release/"source_manifest.json")
    assert all(p.sha(root/x["path"])==x["sha256"] for x in sources)
    data=p.read_json(release/"dataset.json"); original=p.digest(data); tables=data["tables"]
    rows=tables["soil_composition"]; denom=rows[0]["denominator_pure_rai"]
    pure=sum(r["area_rai"] for r in tables["district_fragments"] if r["kind"]=="pure")
    mixed=sum(r["area_rai"] for r in tables["mixed_exclusions"])
    assert abs(pure-denom)<1e-8 and abs(sum(r["area_rai"] for r in rows)-pure)<p.TOL_RAI
    assert {r["soil_unit"] for r in rows}>=SPECIAL
    assert len({r["soil_unit"] for r in rows})==len(rows)
    top,groups=display_groups(rows)
    names=defaultdict(set)
    reader=shapefile.Reader(str(root/p.SOIL),encoding="cp874")
    for record in reader.iterRecords():
        attrs=record.as_dict(); name=str(attrs.get("soilserien") or "").strip()
        if name and name.lower() not in {"null","none","-"}:
            names[str(attrs["soilseries"]).strip()].add(name)
    # Read only two boundary geometries; no soil/land-use raw geometry or overlay.
    admin=shapefile.Reader(str(root/p.ADMIN),encoding="utf-8")
    selected=[(i,row) for i,row in enumerate(admin.iterRecords()) if str(row.as_dict()["AMPHOE_IDN"])=="2203"]
    assert len(selected)==2
    boundaries=[shape(admin.shape(i).__geo_interface__) for i,_ in selected]
    assert all(g.is_valid for g in boundaries)
    boundary=shapely.union_all(boundaries); assert boundary.is_valid
    soil_table=[{**r,"names_from_source":sorted(names[r["soil_unit"]]),
                 "name_source":"soil.dbf:soilserien" if names[r["soil_unit"]] else None} for r in rows]
    p.write(out/"soil_composition_summary.json",{"denominator":"all Pure A403 clipped to Tha Mai, includes SC/W/Uncovered",
        "denominator_pure_rai":denom,"mixed_excluded_rai":mixed,"rows":soil_table,
        "source_dataset_sha256":meta["dataset_sha256"],"public_release":"HOLD"})
    colors=dict(zip([r["soil_unit"] for r in rows if r["soil_unit"] in top],
                    ["#007f86","#4263a3","#c7922f","#9470aa","#62a78c","#dc7960"]))
    colors.update({"OTHER":"#c1cbd0","SC":"#424952","W":"#248dde","UNCOVERED":"#191919"})
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Patch
    from shapely.plotting import patch_from_polygon
    fig,axes=plt.subplots(1,3,figsize=(18,11)); fig.subplots_adjust(left=.045,right=.985,top=.83,bottom=.30,wspace=.18)
    map_counts=defaultdict(int); map_areas=defaultdict(float)
    def paint(ax,records,color,role):
        patches=[]
        for row in records:
            g=shapely.from_wkt(row["geometry_wkt"])
            assert p.geom_hash(g)==row["geometry_sha256"]
            # Full-resolution inputs; polygon paths preserve interior rings.
            patches.extend(patch_from_polygon(part) for part in ([g] if g.geom_type=="Polygon" else g.geoms))
            map_counts[role]+=1; map_areas[role]+=row["area_rai"]
        if patches: ax.add_collection(PatchCollection(patches,facecolor=color,edgecolor="none",zorder=2))
    pure_rows=[r for r in tables["district_fragments"] if r["kind"]=="pure"]
    paint(axes[0],pure_rows,"#007f86","pure_panel1")
    for key,color in colors.items():
        records=[r for r in tables["soil_intersections"] if (r["soil_unit"] if r["soil_unit"] in top|SPECIAL else "OTHER")==key]
        if key=="UNCOVERED": records=tables["uncovered"]
        paint(axes[1],records,color,"soil_"+key)
    paint(axes[2],tables["mixed_exclusions"],"#d58336","mixed_panel3")
    paint(axes[2],pure_rows,"#007f86","pure_panel3")
    a,b,c,d=boundary.bounds
    for ax,title in zip(axes,["01  Boundary + Pure A403","02  Soil within Pure A403","03  Pure / excluded mixed-use"]):
        for part in ([boundary] if boundary.geom_type=="Polygon" else boundary.geoms):
            ax.plot(*part.exterior.xy,lw=.8,color="#1d3842",zorder=4)
            for ring in part.interiors: ax.plot(*ring.xy,lw=.8,color="#1d3842",zorder=4)
        ax.set(xlim=(a-1200,c+1200),ylim=(b-1200,d+1200),aspect="equal")
        ax.set_facecolor("#f5f7f7"); ax.set_title(title,fontsize=13,fontweight="bold",loc="left",pad=15)
        ax.ticklabel_format(style="plain",useOffset=False); ax.tick_params(labelsize=7)
        ax.set_xlabel("UTM Easting (m)",fontsize=8)
        x,y=a+900,b+900; length=5000
        ax.plot([x,x+length],[y,y],lw=3,color="#1d3842",zorder=5)
        ax.text(x+length/2,y+500,"5 km (grid)",ha="center",fontsize=8,zorder=5)
        ax.annotate("N",xy=(.92,.91),xytext=(.92,.82),xycoords="axes fraction",ha="center",fontsize=11,
                    arrowprops={"arrowstyle":"->","color":"#1d3842"})
    axes[0].set_ylabel("UTM Northing (m)",fontsize=8)
    axes[0].legend(handles=[Patch(color="#007f86",label="Pure A403"),Patch(facecolor="none",edgecolor="#1d3842",label="Tha Mai boundary")],
                   loc="upper left",bbox_to_anchor=(0,-.10),fontsize=9,frameon=False)
    handles=[Patch(color=colors[key],label=("Other (display only)" if key=="OTHER" else "Uncovered" if key=="UNCOVERED" else key)
                   +(f"  {area/denom*100:.4f}%" if key in SPECIAL else f"  {area/denom*100:.2f}%")) for key,area in groups.items()]
    axes[1].legend(handles=handles,loc="upper left",bbox_to_anchor=(0,-.10),ncol=2,fontsize=8,frameon=False)
    axes[2].legend(handles=[Patch(color="#007f86",label=f"Pure: {pure:,.2f} rai"),
        Patch(color="#d58336",label=f"Mixed excluded: {mixed:,.2f} rai")],loc="upper left",bbox_to_anchor=(0,-.10),fontsize=9,frameon=False)
    fig.suptitle("THA MAI | Spatial soil research preview",fontsize=23,fontweight="bold",color="#1d3842",y=.965)
    fig.text(.045,.90,"QC POLICY v2: PRIMARY PASS  |  INTERNAL ONLY  |  PUBLIC HOLD",fontsize=12,color="#007f86")
    fig.text(.045,.025,"LDD land-use map: 2568 | Soil production: 2561 | EPSG:32647 / WGS 84 UTM 47N | 1 rai = 1,600 m2\n"
        "Sources: LDD provincial land-use, soil and administrative layers (sealed source manifest). Survey / boundary dates unverified.\n"
        "42 source soil units + Uncovered retained; Other groups 34 ordinary units for display only. Mixed-use fraction unknown, excluded.\n"
        "Not owner-orchard boundaries; no district yield or ready district weather. Geometry warning: two-stage GEOS union +14.2778 rai.",
        fontsize=9,color="#243c46",linespacing=1.7)
    fig.savefig(out/"map_preview.png",dpi=180); plt.close(fig)
    assert map_counts["pure_panel1"]==map_counts["pure_panel3"]==1504
    assert map_counts["mixed_panel3"]==len(tables["mixed_exclusions"])
    assert sum(v for k,v in map_counts.items() if k.startswith("soil_"))==len(tables["soil_intersections"])+len(tables["uncovered"])
    assert abs(sum(v for k,v in map_areas.items() if k.startswith("soil_"))-denom)<p.TOL_RAI
    warning=summary["warnings"]; assert len(warning)==1 and warning[0]["area_difference_rai"]>14
    style="""body{font-family:Tahoma,Arial,sans-serif;color:#183640;margin:0;background:#edf2f4}main{max-width:980px;margin:20px auto;background:white;padding:28px}h1{font-size:26px}h2{font-size:18px;color:#087f86}p,li{font-size:14px;line-height:1.65}table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:6px 9px;border-bottom:1px solid #d5dfe3;text-align:left}td.num{text-align:right;font-variant-numeric:tabular-nums}.tag{font-size:11px;color:#087f86;font-weight:bold;letter-spacing:1px}.note{background:#fff5e5;padding:12px;border-left:4px solid #b46d20}.map{width:100%;height:auto}.page{box-sizing:border-box;page-break-after:always}.page:last-child{page-break-after:auto}footer{font-size:10px;color:#425965;margin-top:15px}@page{size:A4;margin:15mm}@media print{body{background:white}main{margin:0;padding:0;max-width:none}.page{min-height:260mm}p,li{font-size:12px}h1{font-size:23px}h2{font-size:16px}.map{max-height:105mm;object-fit:contain}table{font-size:11px}}"""
    table_rows="".join(f"<tr><td>{escape(r['soil_unit'])}</td><td>{escape(' / '.join(r['names_from_source']) or ('ไม่มีชื่อจาก Source' if r['soil_unit']!='UNCOVERED' else 'ไม่ครอบคลุมแผนที่ดิน'))}</td><td class='num'>{r['area_rai']:,.2f}</td><td class='num'>{r['share_of_all_pure_pct']:.4f}</td></tr>" for r in soil_table)
    head="<tr><th>รหัสหน่วยแผนที่ดิน</th><th>ชื่อจาก Source</th><th>พื้นที่ (ไร่)</th><th>% ของ Pure A403</th></tr>"
    table_html=f"<!doctype html><html lang='th'><meta charset='utf-8'><title>Tha Mai soil composition - Internal</title><style>{style}</style><main><div class='tag'>INTERNAL ONLY · PUBLIC HOLD</div><h1>ท่าใหม่: ตารางองค์ประกอบหน่วยแผนที่ดิน</h1><p>ตัวหาร Pure A403 {denom:,.2f} ไร่ รวม SC, W และ Uncovered; Mixed-use {mixed:,.2f} ไร่แยกออกและไม่เข้าสูตรเปอร์เซ็นต์ ชื่ออ่านจาก soil.dbf / soilserien ไม่ขยายรหัสด้วยการเดา</p><table>{head}{table_rows}</table><p>ตัวเลขปัดเศษเพื่อแสดงผลเท่านั้น ค่าเต็มและ Lineage อยู่ใน soil_composition_summary.json และ Sealed Dataset เดิม</p></main></html>"
    (out/"soil_composition_summary.html").write_text(table_html,encoding="utf-8")
    top_rows="".join(f"<tr><td>{escape(r['soil_unit'])}</td><td>{escape(' / '.join(r['names_from_source']) or 'ไม่พบชื่อ')}</td><td class='num'>{r['area_rai']:,.2f}</td><td class='num'>{r['share_of_all_pure_pct']:.2f}</td></tr>" for r in soil_table[:6])
    special_rows="".join(f"<tr><td>{r['soil_unit']}</td><td>{escape(' / '.join(r['names_from_source']) or 'ไม่พบชื่อจาก Source')}</td><td class='num'>{r['area_rai']:,.2f}</td><td class='num'>{r['share_of_all_pure_pct']:.4f}</td></tr>" for r in soil_table if r['soil_unit'] in SPECIAL)
    brief=f"""<!doctype html><html lang='th'><meta charset='utf-8'><title>ท่าใหม่ - Advisor Research Preview</title><style>{style}</style><main>
    <section class='page'><div class='tag'>THA MAI / ADVISOR RESEARCH PREVIEW / INTERNAL ONLY</div><h1>พื้นที่ทุเรียนและหน่วยแผนที่ดินในท่าใหม่</h1>
    <p>อำเภอท่าใหม่ จังหวัดจันทบุรี (2203) · แผนที่การใช้ที่ดิน 2568 · การผลิตแผนที่ดิน 2561<br>สถานะ: Internal Accepted Release Proposal ภายใต้ QC Policy v2 / <b>Public HOLD</b></p>
    <h2>โจทย์สำหรับหารืออาจารย์</h2><p>พื้นที่ที่รหัสการใช้ที่ดินเป็น Pure A403 ภายในอำเภอมีองค์ประกอบหน่วยแผนที่ดินอย่างไร และข้อมูลนี้เหมาะเป็นฐานสำหรับศึกษาความแตกต่างเชิงพื้นที่ขั้นต่อไปเพียงใด?</p>
    <img class='map' src='map_preview.png' alt='แผนที่สามแผงแสดงขอบเขต Pure A403 หน่วยแผนที่ดิน และพื้นที่ปลูกผสมที่แยกออก'>
    <h2>ขอบเขตข้อมูลและวิธีแสดงผล</h2><p>ใช้ Persisted Geometry และพื้นที่จาก Phase 10F โดยไม่รัน Overlay ใหม่: Pure A403 <b>{pure:,.2f} ไร่</b> / 1,504 Fragments; Mixed-use ที่แยกออก <b>{mixed:,.2f} ไร่</b> / {len(tables['mixed_exclusions']):,} Fragments ไม่ทราบสัดส่วนทุเรียนในพื้นที่ผสม จึงไม่จัดสรรหรือรวมในตัวหาร</p>
    <p>42 หน่วยแผนที่ดิน + Uncovered; Legend แสดง Top 6 + Other + SC/W/Uncovered เฉพาะเพื่ออ่านภาพ ตารางเต็มยังคงทุกหน่วยและค่าเดิม Scale Bar เป็นระยะบน Grid UTM ไม่ใช่ความแม่นตำแหน่งภาคสนาม</p>
    <footer>แหล่งข้อมูล: กรมพัฒนาที่ดิน (LDD), ชั้น Land-use / Soil / Administrative Boundaries ตาม Source Manifest เดิม · EPSG:32647 · 1 ไร่ = 1,600 m²<br>ปีแผนที่/ปีผลิตไม่ใช่วันที่สำรวจที่ยืนยันแล้ว; Boundary Effective Date และสิทธิ์เผยแพร่ยังไม่ยืนยัน · 1 / 2</footer></section>
    <section class='page'><div class='tag'>EVIDENCE / LIMITATIONS / ADVISOR DECISIONS</div><h1>ผลเชิงพรรณนาและข้อจำกัด</h1>
    <h2>หน่วยที่มีพื้นที่มากที่สุด และหมวดที่ต้องแยกอ่าน</h2><table>{head}{top_rows}{special_rows}</table>
    <p>ตัวหารทุกแถวคือ Pure A403 ทั้งอำเภอ {denom:,.2f} ไร่; SC และ W เป็นหมวดแผนที่ ไม่ตีความเป็นชุดดินที่ยืนยันแล้ว Uncovered มีพื้นที่เล็กกว่า 0.005 ไร่และแสดงปัดเศษเป็น 0.00 ไม่ได้ Drop Geometry ตารางเต็ม 43 แถวอยู่ในเอกสารประกอบ</p>
    <h2>Display QC และ Geometry Warning</h2><p>Phase 10F ตรวจผ่าน 1,504 Pure Fragments และ 3,025 Parent Partitions; 90,691 Primary Checks ไม่มี Failed / Inconclusive การแสดงผลตรวจ IDs, Geometry Hashes, จำนวนชิ้น และพื้นที่เทียบ Sealed Dataset; Other ไม่เปลี่ยนค่าต้นฉบับ</p>
    <div class='note'><b>คำเตือนที่ยังคงอยู่:</b> GEOS 3.13.1 Two-stage Union ของ cti_2568_25042_2203_0 ละเมิด Area Upper Bound {warning[0]['area_difference_rai']:.4f} ไร่ และเติมรูเดิม Primary Checks ของ Original Partition ผ่านภายใต้ Policy v2 จึงเก็บเป็น Diagnostic Warning ไม่ใช่การแก้ Kernel หรือรับรองข้าม Engine</div>
    <h2>สิ่งที่ข้อมูลนี้ยังตอบไม่ได้</h2><ul><li>ไม่มี Yield รายอำเภอ: ห้ามใช้ OAE ระดับจังหวัดแทนผลผลิตของท่าใหม่</li><li>ไม่มีขอบเขตหรือพิกัดสวนรายเจ้าของที่ยืนยันแล้ว: A403 คือหน่วยแผนที่การใช้ที่ดิน ไม่ใช่สวนแต่ละเจ้าของ</li><li>Weather รายอำเภอยังไม่พร้อม: ไม่ใช้ Weight ของจังหวัดแทน และไม่ถือจุด NASA POWER เป็นสถานีอิสระ</li><li>ไม่ยืนยัน Spatial Accuracy ภาคสนาม/Survey Date; Footprint ปี 2568 ไม่ใช่ประวัติพื้นที่ปลูกทุกปี และสิทธิ์เผยแพร่ยัง Pending</li></ul>
    <h2>คำถามที่ควรตัดสินใจก่อนขยาย</h2><p>เลือกหน่วยศึกษาต่อเป็นอำเภอหรือกลุ่ม Soil Map Units? ต้องตรวจภาคสนาม/ขอข้อมูลขอบเขตสวนใดก่อน? จะออกแบบ Weather Profile ตามพื้นที่จริงและตรวจ Unique Grids อย่างไร? การขยายอีก 9 อำเภอต้องอนุมัติแยก</p>
    <footer>Source Attribution: LDD และ Source Manifest ที่ตรวจ Hash แล้ว · Dataset SHA256 {meta['dataset_sha256'][:16]}…<br>Internal Research Only / Public HOLD · ไม่มี Yield Analysis, Causal Claim หรือ Historical PIT Certification · 2 / 2</footer></section></main></html>"""
    (out/"advisor_brief.html").write_text(brief,encoding="utf-8")
    assert p.digest(data)==original and p.sha(release/"dataset.json")==meta["dataset_sha256"]
    changed=[k for k,v in before.items() if not (root/k).exists() or p.sha(root/k)!=v]; assert not changed,changed
    p.write(out/"display_qc.json",{"status":"pass","dataset_sha256":meta["dataset_sha256"],"code_sha256":p.sha(__file__),
        "soil_summary_rows":len(rows),"original_values_retained":True,"denominator_pure_rai":denom,
        "mixed_excluded_rai":mixed,"display_groups_rai":groups,"map_record_counts":dict(map_counts),
        "map_area_totals_rai":dict(map_areas),"boundary_source_records":[i for i,_ in selected],
        "boundary_geometry_sha256":p.geom_hash(boundary),"scale_bar_grid_metres":5000,
        "geometry_warnings":warning,"raw_overlay_rerun":False,"public_release":"HOLD",
        "protected_files_checked":len(before),"protected_changes":[]})
    print({"display_qc":"pass","pure_rai":pure,"mixed_excluded_rai":mixed,"soil_rows":len(rows),"protected_unchanged":len(before)})


if __name__=="__main__": main()
