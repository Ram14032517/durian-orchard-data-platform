import {jsx as nativeJsx,jsxs as nativeJsxs,Fragment} from 'react/jsx-runtime';
import {translatedProps} from '../../../i18n/language.js';
export {Fragment};
export const jsx=(type,props,key)=>nativeJsx(type,translatedProps(type,props),key);
export const jsxs=(type,props,key)=>nativeJsxs(type,translatedProps(type,props),key);
