"""
Script build knowledge base Dr.Bee Nhong Ong Haircare.

Chay:
    python data/build_kb_drbee.py

Output: fay_player_knowledge/drbee-nhuong-ong-haircare.zip
MCP server tu detect va load trong 60 giay.
"""
import zipfile
import json
import os

SECTIONS = [
    {
        'id': 's01',
        'title': 'Nhong Ong Haircare la gi?',
        'script': (
            "Nhong Ong Haircare la dong san pham cham soc toc cao cap cua Dr.Bee, "
            "duoc san xuat tai Can Tho, Viet Nam.\n\n"
            "San pham da duoc Bo Y Te cap phep, an toan tuyet doi.\n"
            "KHONG SLS, KHONG Paraben, KHONG Silicone.\n\n"
            "Diem khac biet cot loi: thay vi chi lam sach be mat nhu cac dau goi "
            "thong thuong, Nhong Ong Haircare dieu tri TAN GOC cac van de da dau "
            "bang cong nghe sinh hoc tu tinh chat nhong ong.\n\n"
            "Fanpage Dr.Bee: https://www.facebook.com/profile.php?id=100092293536330"
        ),
    },
    {
        'id': 's02',
        'title': 'So sanh voi dau goi thong thuong',
        'script': (
            "DAU GOI PHO THONG (Clear, Sunsilk, Pantene):\n"
            "- Chi chong gau tuc thoi, khong tri goc re.\n"
            "- Chua SLS/SLES, Silicon, Paraben - bao mon da dau, gay rebound (gau quay lai nang hon).\n"
            "- Huong lieu tong hop gay kich ung da nhay cam.\n"
            "- Khong diet nam Malassezia, khong can bang ba nhon.\n\n"
            "NHONG ONG HAIRCARE:\n"
            "- Dieu tri tu goc: enzyme, protein sinh hoc & khang sinh tu nhien tu nhong ong.\n"
            "- Vo hieu hoa nam Malassezia tan goc.\n"
            "- Dieu hoa ba nhon - can bang moi truong da dau.\n"
            "- Tai tao te bao - chua lanh mo viem va ton thuong.\n"
            "- Khong gay tai phat, khong bao mon, khong tac dung phu.\n\n"
            "Ly do khach doi sang Nhong Ong:\n"
            "- Cam nhan su 'diu' ngay sau 1 tuan.\n"
            "- Het ngua, it rung, da dau khoe, toc moc con.\n"
            "- Thom nhe tu nhien, khong mui hoa chat.\n"
            "- Trai nghiem cham soc nhu Spa tai nha.\n\n"
            "Cau chot sale: 'Chi a, Sunsilk la make up cho toc, con Nhong Ong la duong tu goc. "
            "Muot gia thi nhanh hong - Muot that thi can phuc hoi a!'"
        ),
    },
    {
        'id': 's03',
        'title': 'Tai sao KHONG SLS Paraben Silicone',
        'script': (
            "SLS / SLES (Sodium Lauryl Sulfate):\n"
            "- Chat tao bot tu dau mo, ban dau dung trong nuoc rua bat va tay rua xe hoi.\n"
            "- Lam sach qua muc, bao mon lop bao ve da dau tu nhien.\n"
            "- Gay kho, ngua, kich ung, bung phat gau tro lai manh hon (rebound).\n\n"
            "Paraben (Methylparaben, Propylparaben):\n"
            "- Chat bao quan co cau truc giong estrogen, gay roi loan noi tiet to.\n"
            "- EU va Nhat da cam hoac gioi han su dung trong my pham.\n"
            "- Co the tich tu trong mo co the theo thoi gian.\n\n"
            "Silicone (Dimethicone, Amodimethicone):\n"
            "- Tao lop mang bong ao tren toc - muot ngay nhung bit tac nang toc.\n"
            "- Toc ngay cang yeu, xo, rung nhieu hon neu dung lau.\n\n"
            "Hau qua dung dau goi thuong nhieu nam:\n"
            "- Gau man tinh, ngua tai phat lien tuc.\n"
            "- Rung toc ngay cang nhieu.\n"
            "- Da dau yeu, nhay cam, kich ung.\n"
            "- Phu nu sau sinh de viem, man, stress.\n\n"
            "Nhong Ong Haircare: KHONG SLS, KHONG Paraben, KHONG Silicone.\n"
            "An toan cho: phu nu sau sinh, da dau nhay cam, nguoi bi gau nam nhieu nam."
        ),
    },
    {
        'id': 's04',
        'title': 'Thanh phan chinh va hoat chat',
        'script': (
            "1. Tinh chat Nhong Ong (Doc quyen - trang trai ong huu co tai Can Tho):\n"
            "- Diet nam Malassezia Globosa - nguyen nhan chinh gay gau, ngua.\n"
            "- Can bang tuyen ba nhon, giam tiet dau thua.\n"
            "- Phuc hoi va tai tao te bao da dau bi ton thuong.\n\n"
            "2. Nhan Sam (vung nui Tay Bac, chuan huu co):\n"
            "- Kich thich moc toc: tang tuan hoan mau duoi da dau.\n"
            "- Ngan rung toc: cu co chan toc.\n"
            "- Khang viem va chong oxy hoa.\n\n"
            "3. Collagen Peptide (thuy phan tu ca bien sau):\n"
            "- Tai tao cau truc toc, giam gay rung, tang do dan hoi.\n"
            "- Phuc hoi da dau, giu am, lam mem mai.\n\n"
            "4. Vitamin B tong hop (Biotin B7, Niacinamide B3, Panthenol B5, Pyridoxine B6):\n"
            "- Nuoi duong nang toc, thuc day trao doi chat.\n"
            "- Kiem soat dau, giam viem da dau.\n\n"
            "5. La Du Du Duc va Hoa Du Du Duc:\n"
            "- Enzyme Papain, chong oxy hoa.\n"
            "- Khang viem, lam diu, thanh loc da dau.\n\n"
            "6. Bao quan: Sodium Benzoate (chuan Bo Y Te, an toan trong my pham)."
        ),
    },
    {
        'id': 's05',
        'title': 'Combo va gia ban',
        'script': (
            "GIA BAN LE: 280.000 VND / 1 hop.\n\n"
            "COMBO 1 - Lieu Trinh Detoxx 60 Ngay:\n"
            "- Gia goc: 840.000 VND. Gia ban: 599.000 VND.\n"
            "- Goi: 1 Dau Goi + 1 Dau Xa + 1 Bot Goi.\n"
            "- Muc tieu: Het gau, het ngua, giam rung ro ret sau 30 ngay.\n"
            "- Qua tang: Ebook cham soc toc + 1 Mu U Dien Di Tinh Chat.\n\n"
            "COMBO 2 - Lieu Trinh Dieu Tri Dut Diem 4 Thang:\n"
            "- Gia goc: 1.680.000 VND. Gia ban: 1.100.000 VND.\n"
            "- Goi: 2 Dau Goi + 2 Dau Xa + 2 Bot U.\n"
            "- Muc tieu: Phuc hoi toan dien, toc moc day sau 90 ngay.\n"
            "- Qua tang: 1 Mu Dien Di Tinh Chat + 1 May Say Dyson + 1 Bo Mat Na Vang 24K.\n"
            "- Tong gia tri qua tang: 600.000 VND.\n"
            "- Tang them: Mentor 1-1 online.\n\n"
            "CAM KET CUA DR.BEE:\n"
            "- Cai thien tiet dau, toc moc nhanh, da dau bot ngua ro ret sau 7 NGAY.\n"
            "- HOAN TIEN 100% neu sau 15 ngay khong co cai thien khi tuan thu dung phac do.\n\n"
            "Luu y chot don: Ngay thu 7 goi dien chot don moi de hang kip giao luc goi cu vua het."
        ),
    },
    {
        'id': 's06',
        'title': 'USP va script tu van sale',
        'script': (
            "CAC Y CHINH KHI TU VAN KHACH HANG:\n"
            "1. It bot xa phong = KHONG SLS/Paraben/Silicon (tot, khong phai xau).\n"
            "2. Bai thuoc Dong Y ket hop Duoc tinh Tay Y.\n"
            "3. Hoat chat cao - Dac tri gau mang, viem da tiet ba, rung toc.\n"
            "4. Organic thuan thien nhien - Dung duoc cho me bau, phu nu sau sinh.\n"
            "5. Bo Y Te cap phep, co kiem nghiem lam sang.\n\n"
            "DIEM BAN HANG DOC DAO (USP):\n"
            "- Tinh chat Nhong Ong Doc quyen: khac biet hoan toan thi truong.\n"
            "- KHONG hoa chat doc hai: tuyet doi an toan.\n"
            "- Hieu qua toan dien: tri gau + giam rung + kich moc + nuoi duong.\n"
            "- Khoa hoc chung minh, Bo Y Te cap phep.\n"
            "- Trai nghiem cham soc dang cap tai nha.\n\n"
            "CAU CHOT SALE:\n"
            "- 'Sunsilk la make up cho toc, Nhong Ong la duong tu goc. Muot gia nhanh hong, muot that can phuc hoi.'\n"
            "- 'Cam ket hoan 100% tien sau 15 ngay neu khong hieu qua - chi khong co rui ro gi ca.'\n"
            "- 'Da dau chi can chua goc, khong phai che phu. Nhong Ong chinh la giai phap do.'"
        ),
    },
]

MANIFEST = {
    'id': 'drbee-nhuong-ong-haircare',
    'title': 'Dr.Bee — Nhong Ong Haircare',
    'author': 'Dr.Bee',
    'version': '1.0.0',
    'color': '#f5a623',
    'icon': '🐝',
    'description': 'Kien thuc san pham Nhong Ong Haircare — danh cho AI tu van ban hang',
    'sections': [],
}

OUT_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', 'fay_player_knowledge', 'drbee-nhuong-ong-haircare.zip'
)


def build():
    manifest = dict(MANIFEST)
    manifest['sections'] = []
    for i, s in enumerate(SECTIONS):
        idx = str(i + 1).zfill(2)
        manifest['sections'].append({
            'id': s['id'],
            'title': s['title'],
            'script': f"sections/{idx}-{s['id']}/script.txt",
            'assets': [],
            'quiz': '',
        })

    out = os.path.normpath(OUT_PATH)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for i, s in enumerate(SECTIONS):
            idx = str(i + 1).zfill(2)
            folder = f"sections/{idx}-{s['id']}/"
            zf.writestr(folder, '')
            zf.writestr(f"{folder}script.txt", s['script'])

    print(f"[OK] {out}")
    print(f"     {len(SECTIONS)} sections, {os.path.getsize(out)} bytes")


if __name__ == '__main__':
    build()
