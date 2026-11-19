# Padé 四个候选的统一排序

接续 [Padé 归约的独立验收与专组交接](https://github.com/epsilon-lain/yohaku/blob/3cfb0a435394bff29988cab3f0f1ffa6c6bca7a4/research/pi-equivalence-native-2026-11-18/HANDOFF.zh.md)。对每个整数 $n\ge2$，Yohaku 的分数 $L(n,m)$ 在所有整数次数 $m\ge2n$ 上严格递增。因此四个预注册候选中统一以 $m=8n$ 最大。准确的共同极限是 $n|\sin n|/(|\sin n|+|\cos n|)$。这把候选的选择从有限经验变成了一个全范围结果，也明确了证明坏逼近性缺少的仍是统一正下界。

## 模长的正系数恒等式

令 $P_m$ 为交接中的 Padé 多项式。对所有实数 $x$ 有
$$
 |P_m(ix)|^2=\sum_{r=0}^{m} c_{m,r}x^{2r},\qquad
 c_{m,r}=\binom{2m-2r}{m-r}\frac{(2m-r)!}{r!}.
$$
将 $P_m$ 的系数公式代入，可核对 $zP_m''-(z+2m)P_m'+mP_m=0$。因此 $e^{-z/2}P_m(z)$ 与 $e^{z/2}P_m(-z)$ 都满足 $y''-(2m/z)y'-y/4=0$。两者的乘积 $W$ 满足
$$
 z^2W'''-6mzW''+(2m+8m^2-z^2)W'+2mzW=0.
$$
这是对乘积求三次导数并代入两个二阶方程得到的。写 $W=\sum_{r=0}^m(-1)^r c_{m,r}z^{2r}$，对比 $z^{2r-1}$ 的系数，得
$$
 \frac{c_{m,r}}{c_{m,r-1}}
 =\frac{2(m-r+1)}{(2r)(2m+1-2r)(4m+2-2r)}.
$$
结合 $c_{m,0}=((2m)!/m!)^2$ 即得恒等式。

仍用交接中的 $D_m=|A_m|+|B_m|$、$U_m=(2n)^{2m+1}m!/(2m+1)!$。取 $x=2n$，模长恒等式保证 $D_m\ge(2m)!/m!$。对 $m\ge2n$，
$$
 \frac{U_m}{D_m}
 \le \frac{(2n)^{2m+1}}{(2m+1)\prod_{j=1}^m(m+j)^2}
 < 2^{-m-1}.
$$
最后一步将乘积中的 $(m+j)$ 与 $(2m+1-j)$ 配对，其积至少是 $2m^2$。

## 四个候选趋向同一精确量

记 $H_n=|\sin n|+|\cos n|$、$F_n=n|\sin n|/H_n$。由交接中的余项，
$$
 R_m=e^{2in}\overline{P_m(2in)}-P_m(2in)
     =2ie^{in}(A_m\sin n-B_m\cos n).
$$
取绝对值并使用反三角不等式，
$$
 \left|\frac{|B_m|}{D_m}-\frac{|\sin n|}{H_n}\right|
 \le \frac{|R_m|}{2D_mH_n}.
$$
由于 $L(n,m)/n=|B_m|/D_m-U_m/(2D_m)$ 且 $|R_m|\le U_m$，得到精确单边误差
$$
 0\le F_n-L(n,m)\le \frac{nU_m}{D_m}< n2^{-m-1}\qquad(m\ge2n).
$$
该结论适用于任意 $n\ge2$，甚至单取 $m=2n$ 也有同样的下极限。只需注意，有界的 $n|\sin n|$ 子列满足 $|\sin n|\to0$ 和 $H_n\to1$。Yohaku 已有的配对恒等式于是给出
$$
 \liminf_{n\to\infty}L(n,2n)
 =\liminf_{n\to\infty}n|\sin n|
 =\pi\liminf_{q\to\infty}q\lVert q\pi\rVert .
$$

## 严格排序

写 $r_m=U_m/(2D_m)$，并定义
$$
 \rho_m(x)=
 \frac{\int_{-1}^1(1-v^2)^m\cos(xv)\,dv}{\int_{-1}^1(1-v^2)^m\,dv}.
$$
将交接中余项积分的变量换成 $v=2t-1$ 得 $R_m=ie^{in}U_m\rho_m(n)$。上节的估计于是给出
$$
 r_m(1-|\rho_m(n)|)\le (F_n-L(n,m))/n
 \le r_m(1+|\rho_m(n)|).
$$

分部积分一次得 $\rho_m''+(2m+2)\rho_m'/x+\rho_m=0$。令 $h=x^{m+1}\rho_m$，则 $h''=(m(m+1)/x^2-1)h$。在 $x=0$ 右侧，$h$ 与 $h'$ 都为正。在 $0<x\le\sqrt{m(m+1)}$ 内，只要 $h>0$ 就有 $h''\ge0$，故 $h$ 保持递增且全程为正。由二阶方程积分，
$$
 -\rho_m'(x)=x^{-2m-2}\int_0^x t^{2m+2}\rho_m(t)\,dt.
$$
先得 $\rho_m$ 递减，再用积分中 $\rho_m(t)\ge\rho_m(x)$，得到 $-\rho_m'/\rho_m\ge x/(2m+3)$。在 $n\le m/2$ 时取 $x=n$ 并积分，得到
$$
 0<\rho_m(n)\le e^{-n^2/(4m+6)},\qquad
 1-\rho_m(n)\ge\frac{n^2}{4m+6+n^2}.
$$

同时，对于 $0\le r\le m$，正系数恒等式给出
$$
 \frac{c_{m+1,r}}{c_{m,r}}
 =\frac{2(2(m-r)+1)}{m-r+1}(2m-r+1)(2m-r+2)
 \ge 2(m+1)(m+2).
$$
用 $|P_m(2in)|\le D_m\le\sqrt2\,|P_m(2in)|$ 和 $U_{m+1}/U_m=(2n)^2/[2(2m+3)]$ 得
$$
 \frac{r_{m+1}}{r_m}
 \le \frac{2n^2}{(2m+3)\sqrt{(m+1)(m+2)}}
 <\frac{n^2}{(m+1)^2}.
$$
若 $m\ge14$ 且 $n\le m/2$，则 $(m+1)^2>2(4m+6+n^2)$，因此 $2r_{m+1}<r_m(1-\rho_m(n))$。代入两边的误差界可知 $F_n-L(n,m+1)<F_n-L(n,m)$。余下的 $2\le n\le6$、$2n\le m<14$ 共 30 对，使用整数交叉相乘已逐对严格核验。

## 从读回的有限检验推广到全体正整数

Mahler 对正整数 $p,q\ge2$ 证明了显式不等式 $|\pi-p/q|>q^{-42}$。[原论文重印](https://ems.press/content/book-chapter-files/27418) 对 $n\ge256$，令 $q$ 为距 $n/\pi$ 最近的整数，则 $2\le q\le n/2$，而 $d=|n-q\pi|$ 落在 $[0,\pi/2]$。于是 $\sin d\ge2d/\pi$，从而
$$
 F_n\ge\frac{2n}{\pi\sqrt2}d>\frac n4(n/2)^{-41}.
$$
令 $2^k\le n<2^{k+1}$，则 $k\ge8$ 且 $2n-2\ge2^{k+1}-2>41k>41\log_2(n/2)$。这说明
$$
 0\le F_n-L(n,m)<n2^{-2n-1}<\frac n8(n/2)^{-41}.
$$
在 $2\le n<256$，对 $m=2n$ 另以整系数 Horner 法精确核对全部 254 个阈值，并使用已经建立的次数单调性。综上，每个整数 $n\ge2$ 和 $m\ge2n$ 都有 $L(n,m)>n^{-40}$。这个统一公式随 $n$ 变小到零，仍需一个不随 $n$ 变小的正数下界才能证明 $\pi$ 坏逼近。
