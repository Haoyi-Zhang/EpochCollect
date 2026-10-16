"""Direct Python vector figures from retained data and the stated construction."""
import argparse
import csv
from fractions import Fraction
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[1]
NAMES=("fork","horizon","envelope","candidates")
plt.rcParams.update({"font.family":"STIXGeneral","mathtext.fontset":"stix",
 "font.size":8,"axes.labelsize":8,"xtick.labelsize":8,"ytick.labelsize":8,
 "legend.fontsize":7.5,"text.usetex":False,"pdf.fonttype":42,"ps.fonttype":42,
 "axes.unicode_minus":False,"axes.linewidth":.6,"lines.linewidth":.8})
META={"Creator":"Python Matplotlib","Producer":None,"CreationDate":None,"ModDate":None}

def read_inputs(root=ROOT):
    data=root/"results/horizon"
    lines=(data/"broadcast-envelope.dat").read_text(encoding="utf-8").splitlines()
    envelope=[dict(zip(lines[0].split(),line.split(),strict=True))
              for line in lines[1:] if line.strip()]
    for row in envelope:
        rho=Fraction(row["rho"])
        for key,exact in (("selective",min(41+3*rho,38+5*rho)),
                          ("saturated",43+3*rho)):
            if abs(Fraction(row[key])-exact)>Fraction(1,10**10):
                raise ValueError(key+" envelope disagrees with exact frontier")
    with (data/"stress-paired.csv").open(encoding="utf-8",newline="") as stream:
        pairs=list(csv.DictReader(stream))
    if len(pairs)!=174 or len({r["case"] for r in pairs})!=174:
        raise ValueError("expected all 174 distinct common-completion cases")
    if any(int(r[k])<=0 for r in pairs for k in ("horizon","prefix")):
        raise ValueError("logarithmic candidate counts must be positive")
    return envelope,pairs

def save(fig,out,name):
    fig.canvas.draw()
    if plt.rcParams["text.usetex"]:
        raise ValueError("LaTeX rendering is not used")
    out.mkdir(parents=True,exist_ok=True)
    fig.savefig(out/(name+".pdf"),metadata=META)
    plt.close(fig)

def fork(out):
    fig=plt.figure(figsize=(3.35,1.72))
    ax=fig.add_axes([0,0,1,1],xlim=(-.5,4.5),ylim=(-1.7,.8));ax.axis("off")
    pos={"a0":(0,0),"b0":(1,0),"a1":(2,0),"b1":(3,0),"a2":(4,0),
         "l0":(0,-.95),"l1":(2,-.95),"l2":(4,-.95)}
    for name,(x,y) in pos.items():
        ax.add_patch(Rectangle((x-.21,y-.18),.42,.36,facecolor="white",
                               edgecolor="black",linewidth=.6))
        letter=r"\ell" if name[0]=="l" else name[0]
        ax.text(x,y,"$"+letter+"_"+name[1]+"$",ha="center",va="center",fontsize=8.5)
        pair=("q" if name[0]=="b" else "p")+"_"+name[1]
        ax.text(x,y+(.32 if name[0]!="l" else -.32),"$"+pair+"$",ha="center",va="center")
    for left,right in (("a0","b0"),("b0","a1"),("a1","b1"),("b1","a2"),
                       ("a0","l0"),("a1","l1"),("a2","l2")):
        x,y=pos[left];xx,yy=pos[right];vertical=y!=yy
        ax.add_patch(FancyArrowPatch((x,y-.18) if vertical else (x+.21,y),
                     (xx,yy+.18) if vertical else (xx-.21,yy),
                     arrowstyle="-|>",mutation_scale=7,linewidth=.6,color="black"))
    ax.text(2,-1.52,r"Precedence arrows; $a_i,b_i$: unit service; $\ell_i$: service $L$.",
            ha="center",va="center",fontsize=7.5)
    save(fig,out,"fork")

def horizon(out):
    fig=plt.figure(figsize=(3.35,2.1))
    ax=fig.add_axes([0,0,1,1],xlim=(-3.4,22.4),ylim=(-1.65,5.5));ax.axis("off")
    ax.text(-3.25,5.12,"Saturation on maximal matchings",ha="left",va="center")
    ax.text(-3.25,2.33,"Whole-task horizon admission",ha="left",va="center")
    rows=(("a",0,1,4.3),("b",10,11,4.3),("c",11,21,4.3),("d",0,10,3.45),
          ("a",0,1,1.5),("b",1,2,1.5),("c",2,12,1.5),("d",1,11,.65))
    for label,start,end,y in rows:
        ax.add_patch(Rectangle((start,y-.3),end-start,.6,edgecolor="black",
            facecolor=".9" if label in ("b","d") else "white",linewidth=.6))
        ax.text((start+end)/2,y,"$"+label+"$",ha="center",va="center",fontsize=7.5)
    for y,label in ((4.3,r"$a,b,c$"),(3.45,r"$d$"),(1.5,r"$a,b,c$"),(.65,r"$d$")):
        ax.text(-.45,y,label,ha="right",va="center",fontsize=7.5)
    for x,lo,hi in ((10,3.03,4.72),(1,.23,1.92)):
        ax.plot([x,x],[lo,hi],ls="--",color="black",lw=.6)
    ax.annotate("",xy=(22,-.25),xytext=(0,-.25),
                arrowprops={"arrowstyle":"->","linewidth":.6})
    for tick in (0,5,10,15,20):
        ax.plot([tick,tick],[-.18,-.32],color="black",lw=.5)
        ax.text(tick,-.46,str(tick),ha="center",va="top",fontsize=7.5)
    ax.text(11,-1.22,"Time (abstract units)",ha="center",va="center")
    save(fig,out,"horizon")

def numerical(out,envelope,pairs):
    fig,ax=plt.subplots(figsize=(3.35,1.85),layout="constrained")
    rho=[float(r["rho"]) for r in envelope]
    for key,label,style in (("selective","Selective / horizon","-"),
                            ("saturated","Saturated","--")):
        ax.plot(rho,[float(r[key]) for r in envelope],style,color="black",label=label)
    ax.plot([1.5,1.5],[36,45.5],":",color=".4",lw=.6)
    ax.text(1.42,38.7,r"$\rho=3/2$",ha="right",fontsize=7.5)
    ax.set(xlim=(0,4),ylim=(36,57),xlabel=r"Setup cost $\rho$",ylabel="Completion time")
    ax.spines[["top","right"]].set_visible(False);ax.grid(alpha=.18,lw=.4)
    ax.legend(loc="upper left",frameon=False);save(fig,out,"envelope")
    fig,ax=plt.subplots(figsize=(3.35,1.95),layout="constrained")
    ax.scatter([int(r["horizon"]) for r in pairs],[int(r["prefix"]) for r in pairs],
               s=13,facecolors="none",edgecolors="black",linewidths=.6,
               label="174 common cases")
    ax.plot([1,1e6],[1,1e6],"--",color=".4",lw=.7,label="Equal candidate count")
    ax.set(xscale="log",yscale="log",xlim=(1,1e6),ylim=(1,1e6),
           xlabel="Horizon candidates",ylabel="Prefix candidates")
    ax.spines[["top","right"]].set_visible(False)
    ax.legend(loc="upper left",frameon=False);save(fig,out,"candidates")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir",type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument("--check-inputs",action="store_true")
    args=ap.parse_args();env,pairs=read_inputs()
    if not args.check_inputs:
        fork(args.outdir);horizon(args.outdir);numerical(args.outdir,env,pairs)
    print("Validated exact envelopes and all 174 paired cases; "+
          ("inputs only." if args.check_inputs else "wrote four vector figures."))
if __name__=="__main__":main()
