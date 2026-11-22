#include "lib9.h"
#include "draw.h"
#include "tk.h"
#include "label.h"

enum { ChromeMeasure, ChromePaint, ChromePress, ChromeRelease };
enum { ChromeHeight = 32 };

int (*tkwmchromecall)(int*, size_t, int*, size_t);

char*
tkwmchrome(TkTop *top, char *arg, char **ret)
{
	static const char *actions[] = {nil, nil, "lower .", "exit", "size", "task", "task", "help", "ok"};
	Tk *tk;
	TkLabel *label;
	TkChrome *chrome;
	TkGeom previous;
	Point screen;
	int request[ChromeRequest] = {0}, reply[6] = {0}, i, action;
	char op[24], name[80], word[32], command[64];

	if(tkwmchromecall == nil)
		return TkBadcm;
	arg = tkword(top, arg, op, op+sizeof(op), nil);
	if(strcmp(op, "available") == 0){
		request[2] = ChromeHeight;
		return tkvalue(ret, "%d", tkwmchromecall(request, nelem(request), reply, 2));
	}
	arg = tkword(top, arg, name, name+sizeof(name), nil);
	tk = tklook(top, name, 0);
	if(tk == nil || tk->type != TKlabel)
		return TkBadwp;
	label = TKobj(TkLabel, tk);
	chrome = label->chrome;
	if(strcmp(op, "setup") == 0){
		tkword(top, arg, word, word+sizeof(word), nil);
		request[2] = ChromeHeight;
		request[3] = atoi(word);
		if(!tkwmchromecall(request, nelem(request), reply, 2))
			return TkBadcm;
		if(reply[0] < 0 || reply[1] <= 0)
			return TkBadvl;
		if(chrome == nil){
			chrome = mallocz(sizeof(TkChrome), 1);
			if(chrome == nil)
				return TkNomem;
			label->chrome = chrome;
		}
		chrome->flags = request[3];
		chrome->width = reply[0];
		chrome->height = reply[1];
		previous = tk->req;
		tksizelabel(tk);
		tkgeomchg(tk, &previous, tk->borderwidth);
		return nil;
	}
	if(chrome == nil)
		return TkBadvl;
	if(strcmp(op, "minsize") == 0)
		return tkvalue(ret, "%d %d", chrome->width, chrome->height);
	if(strcmp(op, "focus") == 0){
		tk->dirty = tkrect(tk, 1);
		tkdirty(tk);
		return nil;
	}
	if(strcmp(op, "press") == 0)
		request[0] = ChromePress;
	else if(strcmp(op, "release") == 0)
		request[0] = ChromeRelease;
	else
		return TkBadop;
	request[1] = tk->act.width;
	request[2] = tk->act.height;
	request[3] = chrome->flags;
	request[4] = top->focused;
	for(i = 5; i <= 6; i++){
		arg = tkword(top, arg, word, word+sizeof(word), nil);
		request[i] = atoi(word);
	}
	arg = tkword(top, arg, word, word+sizeof(word), nil);
	screen.x = atoi(word);
	tkword(top, arg, word, word+sizeof(word), nil);
	screen.y = atoi(word);
	memmove(request+8, chrome->state, sizeof(chrome->state));
	if(request[0] == ChromePress)
		chrome->press = screen;
	else{
		request[13] = screen.x - chrome->press.x;
		request[14] = screen.y - chrome->press.y;
	}
	if(!tkwmchromecall(request, nelem(request), reply, nelem(reply)))
		return TkBadvl;
	memmove(chrome->state, reply+1, sizeof(chrome->state));
	tk->dirty = tkrect(tk, 1);
	tkdirty(tk);
	action = reply[0];
	if(action == 1)
		snprint(command, sizeof(command), "wm_title move %d %d", screen.x, screen.y);
	else if(action > 1 && action < nelem(actions))
		snprint(command, sizeof(command), "wm_title %s", actions[action]);
	else
		return nil;
	return tksend(top, command, ret);
}

static Image *
chromeatlas(Display *display)
{
    static Image *atlas;
    uchar *pixels;
    int fd, size = 84*84*4;

    if(atlas != nil)
        return atlas;
    fd = open("/lib/rill/themes/Sweet-Dark/chrome.rgba", OREAD);
    if(fd < 0)
        return nil;
    pixels = malloc(size);
    if(pixels != nil && readn(fd, pixels, size) == size){
        atlas = allocimage(display, Rect(0, 0, 84, 84), RGBA32, 0, DNofill);
        if(atlas != nil && loadimage(atlas, atlas->r, pixels, size) < 0){
            freeimage(atlas);
            atlas = nil;
        }
    }
    free(pixels);
    close(fd);
    return atlas;
}

static Rectangle
chromerect(const int *fields)
{
	return Rect(fields[0], fields[1], fields[0]+fields[2], fields[1]+fields[3]);
}

static void
chrometext(Image *image, Rectangle r, Font *font, Image *ink, char *text, int center)
{
	Rectangle saved = image->clipr;
	Point p;
	char *shortened = nil;
	int n, dots;

	if(text == nil || *text == '\0' || Dx(r) <= 0 || Dy(r) <= 0)
		return;
	if(center && stringwidth(font, text) > Dx(r)){
		n = strlen(text);
		shortened = malloc(n+4);
		if(shortened == nil)
			return;
		memmove(shortened, text, n+1);
		dots = stringwidth(font, "...");
		while(n > 0 && stringwidth(font, shortened)+dots > Dx(r)){
			n--;
			while(n > 0 && (shortened[n]&0xc0) == 0x80)
				n--;
			shortened[n] = 0;
		}
		strcpy(shortened+n, "...");
		text = shortened;
	}
	p = Pt(r.min.x, r.min.y + (Dy(r)-font->height)/2);
	if(center)
		p.x += (Dx(r)-stringwidth(font, text))/2;
	if(rectclip(&r, saved)){
		replclipr(image, 0, r);
		string(image, p, ink, ZP, font, text);
		replclipr(image, 0, saved);
	}
	free(shortened);
}

int
tkdrawchrome(Tk *tk, Image *dst, Point where)
{
	TkLabel *label = TKobj(TkLabel, tk);
	TkChrome *chrome = label->chrome;
	TkEnv *env = tk->env;
	TkCtxt *context = env->top->ctxt;
	int request[ChromeRequest] = {ChromePaint, tk->act.width, tk->act.height,
		chrome->flags, env->top->focused};
	int *scene = chrome->scene;
	int i, j, sprite;
	Image *image, *ink, *atlas;
	Rectangle r, cell;
	char glyph[5];

	if(tkwmchromecall == nil || tk->act.width <= 0 || tk->act.height <= 0)
		return 0;
	request[12] = chrome->state[4];
	if(!chrome->scenevalid || memcmp(request, chrome->paint, sizeof(request)) != 0){
		chrome->scenevalid = 0;
		memset(scene, 0, sizeof(chrome->scene));
		if(!tkwmchromecall(request, nelem(request), scene, ChromeScene))
			return 0;
		memmove(chrome->paint, request, sizeof(request));
		chrome->scenevalid = 1;
	}
	r = Rect(0, 0, tk->act.width, tk->act.height);
	image = tkitmp(env, r.max, TkCbackgnd);
	if(image == nil)
		return 0;
	draw(image, r, tkcolor(context, scene[0]), nil, ZP);
	ink = tkcolor(context, scene[1]);
	chrometext(image, chromerect(scene+2), env->font, ink, label->text, 1);
	for(i = 6; i < ChromeScene; i += 9){
		cell = chromerect(scene+i);
		if(Dx(cell) <= 2 || Dy(cell) <= 2)
			continue;
		sprite = -scene[i+5]-1;
		if(sprite >= 0 && sprite < 9 && (atlas = chromeatlas(image->display)) != nil){
			Rectangle art = Rect(0, 0, 28, 28);
			art = rectaddpt(art, Pt((cell.min.x+cell.max.x-28)/2, (cell.min.y+cell.max.y-28)/2));
			draw(image, art, atlas, nil, Pt(sprite%3*28, sprite/3*28));
			continue;
		}
		fillellipse(image, Pt((cell.min.x+cell.max.x)/2, (cell.min.y+cell.max.y)/2),
			7, 7, tkcolor(context, scene[i+4]), ZP);
		if(sprite >= 0)
			continue;
		for(j = 0; j < sizeof(glyph)-1; j++)
			glyph[j] = scene[i+5+j];
		glyph[sizeof(glyph)-1] = '\0';
		if(chrome->state[4] != 0)
			chrometext(image, cell, env->font, ink, glyph, 1);
	}
	draw(dst, rectaddpt(r, where), image, nil, ZP);
	return 1;
}
